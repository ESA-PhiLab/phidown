from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import json
import zipfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

tifffile = pytest.importorskip("tifffile")

from phidown.cli import main
from phidown.s1_burst_merge import (
    BurstMergeError,
    _footprint_string,
    _group_footprint,
    _keep_rfi_reports_of_bursts,
    _mark_manifest_assembled,
    _measurement_gcps,
    _merged_grid_points,
    _parent_first_line,
    _rebase_noise_azimuth_vector,
    discover_burst_safes,
    merge_burst_safes,
)


BASE_TIME = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def _product_xml(*, burst_id: int, swath: str = "IW2", pol: str = "VV", start: datetime) -> str:
    stop = start + timedelta(seconds=1)
    iso = lambda value: value.isoformat().replace("+00:00", "Z")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<product>
  <adsHeader>
    <missionId>S1A</missionId><productType>SLC</productType><mode>IW</mode>
    <swath>{swath}</swath><polarisation>{pol}</polarisation>
    <startTime>{iso(start)}</startTime><stopTime>{iso(stop)}</stopTime>
    <absoluteOrbitNumber>123456</absoluteOrbitNumber><missionDataTakeId>789</missionDataTakeId>
    <imageNumber>001</imageNumber>
  </adsHeader>
  <imageAnnotation><imageInformation numberOfLines="2">
    <productFirstLineUtcTime>{iso(start)}</productFirstLineUtcTime>
    <productLastLineUtcTime>{iso(stop)}</productLastLineUtcTime>
    <productComposition>Single</productComposition><sliceNumber>1</sliceNumber>
    <numberOfLines>2</numberOfLines><azimuthTimeInterval>0.5</azimuthTimeInterval>
    <imageStatistics><outputDataMean><re>0</re><im>0</im></outputDataMean>
      <outputDataStdDev><re>0</re><im>0</im></outputDataStdDev></imageStatistics>
  </imageInformation></imageAnnotation>
  <swathTiming><linesPerBurst>2</linesPerBurst><samplesPerBurst>3</samplesPerBurst>
    <burstList count="1"><burst><azimuthTime>{iso(start)}</azimuthTime>
      <sensingTime>{iso(start)}</sensingTime><byteOffset>0</byteOffset><burstId>{burst_id}</burstId>
    </burst></burstList>
  </swathTiming>
  <geolocationGrid><geolocationGridPointList count="2">
    <geolocationGridPoint><line>0</line><pixel>0</pixel><latitude>40</latitude><longitude>10</longitude></geolocationGridPoint>
    <geolocationGridPoint><line>1</line><pixel>2</pixel><latitude>41</latitude><longitude>11</longitude></geolocationGridPoint>
  </geolocationGridPointList></geolocationGrid>
</product>
'''


def _make_burst_safe(
    parent: Path,
    ordinal: int,
    burst_id: int,
    *,
    swath: str = "IW2",
    pol: str = "VV",
    start: datetime | None = None,
) -> Path:
    start = start or (BASE_TIME + timedelta(seconds=ordinal * 2))
    safe = parent / f"S1A_{swath}_SLC__1SDV_20240102T030405_20240102T030406_123456_000789_{ordinal:04X}.SAFE"
    (safe / "measurement").mkdir(parents=True, exist_ok=True)
    (safe / "annotation" / "calibration").mkdir(parents=True, exist_ok=True)
    data = np.array(
        [
            [[ordinal, 1], [ordinal, 2], [ordinal, 3]],
            [[ordinal, 4], [ordinal, 5], [ordinal, 6]],
        ],
        dtype=np.int16,
    )
    measurement = safe / "measurement" / f"s1a-{swath.lower()}-slc-{pol.lower()}-burst-{ordinal:03d}.tiff"
    tifffile.imwrite(
        measurement,
        data,
        metadata=None,
        compression=None,
        rowsperstrip=1,
        photometric="minisblack",
        planarconfig="contig",
    )
    annotation = safe / "annotation" / f"s1a-{swath.lower()}-slc-{pol.lower()}-burst-{ordinal:03d}.xml"
    annotation.write_text(_product_xml(burst_id=burst_id, swath=swath, pol=pol, start=start), encoding="utf-8")
    (safe / "manifest.safe").write_text(
        "<?xml version=\"1.0\"?><XFDU><metadataSection/></XFDU>", encoding="utf-8"
    )
    return safe


def test_product_only_metadata_does_not_create_auxiliary_files(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    output = merge_burst_safes([first], output_dir=tmp_path / "output")

    assert not list((output / "annotation" / "calibration").glob("*.xml"))
    assert not list((output / "annotation" / "rfi").glob("*.xml"))


def test_cdse_burst_safe_names_are_accepted(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101)
    first = first.rename(tmp_path / "inputs" / "S1A_SLC_20240102T030405_000001_IW2_VV_000789.SAFE")
    second = second.rename(tmp_path / "inputs" / "S1A_SLC_20240102T030407_000002_IW2_VV_000789.SAFE")

    output = merge_burst_safes([first, second], tmp_path / "output")

    assert output.is_dir()


def test_auxiliary_annotations_are_written_to_safe_directories(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101)
    (second / "annotation" / "rfi").mkdir(parents=True, exist_ok=True)
    (second / "annotation" / "rfi" / "rfi-test.xml").write_text(
        "<rfi><noiseVectorList count=\"1\"><noiseVector><line>0</line></noiseVector></noiseVectorList></rfi>",
        encoding="utf-8",
    )

    output = merge_burst_safes([first, second], tmp_path / "out")

    rfi = next((output / "annotation" / "rfi").glob("*.xml"))
    assert "<line>2</line>" in rfi.read_text(encoding="utf-8")


def test_merge_burst_safes_concatenates_data_and_rewrites_metadata(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101)

    output = merge_burst_safes([first, second], output_dir=tmp_path / "output")

    assert output.is_dir()
    assert output.suffix == ".SAFE"
    measurement = next((output / "measurement").glob("*.tiff"))
    merged = tifffile.imread(measurement)
    assert merged.shape == (4, 3)
    assert merged.dtype.kind == "c"
    with tifffile.TiffFile(measurement) as tiff:
        page = tiff.pages[0]
        assert page.samplesperpixel == 1
        assert page.bitspersample == 32
        assert page.sampleformat.value == 5
        assert len(page.tags[33922].value) % 6 == 0 and page.tags[33922].value
        assert 4326 in page.tags[34735].value
        burst_offsets = (page.dataoffsets[0], page.dataoffsets[2])
    expected = np.concatenate(
        [tifffile.imread(next((first / "measurement").glob("*.tiff"))), tifffile.imread(next((second / "measurement").glob("*.tiff")))],
        axis=0,
    )
    expected = expected[..., 0] + 1j * expected[..., 1]
    assert np.array_equal(merged, expected)

    annotation = next((output / "annotation").glob("*.xml"))
    text = annotation.read_text(encoding="utf-8")
    assert "<numberOfLines>4</numberOfLines>" in text
    parsed = ET.fromstring(text)
    assert parsed.find("imageAnnotation/imageInformation").get("numberOfLines") is None
    assert '<burstList count="2">' in text
    assert "<burstId>100</burstId>" in text and "<burstId>101</burstId>" in text
    xml_offsets = []
    for item in parsed.findall("swathTiming/burstList/burst"):
        offset = item.find("byteOffset")
        assert offset is not None and offset.text is not None
        xml_offsets.append(int(offset.text))
    assert xml_offsets == list(burst_offsets)
    assert "<line>2</line>" in text

    manifest = (output / "manifest.safe").read_text(encoding="utf-8")
    assert "dataObjectSection" in manifest
    assert measurement.name in manifest
    assert annotation.name in manifest
    assert "./preview/map-overlay.kml" in manifest
    assert "./preview/product-preview.html" in manifest


def test_collection_directory_is_discovered_recursively(tmp_path):
    first = _make_burst_safe(tmp_path / "collection" / "nested", 1, 100)
    second = _make_burst_safe(tmp_path / "collection" / "nested", 2, 101)

    discovered = discover_burst_safes([tmp_path / "collection"])

    assert discovered == [first.resolve(), second.resolve()]


def test_zip_archives_are_extracted_and_merged(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101)
    archive = tmp_path / "bursts.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        for safe in (first, second):
            for file in safe.rglob("*"):
                if file.is_file():
                    zipped.write(file, file.relative_to(tmp_path).as_posix())

    output = merge_burst_safes([archive], tmp_path / "output")

    assert output.is_dir()
    assert len(list((output / "measurement").glob("*.tiff"))) == 1
    assert not list((tmp_path / "output").glob(".phidown-burst-input-*"))


def test_zip_archive_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../outside.txt", "not allowed")

    with pytest.raises(BurstMergeError, match="Unsafe path"):
        merge_burst_safes([archive], tmp_path / "output")

    assert not (tmp_path / "outside.txt").exists()


def test_merge_rejects_missing_burst_in_sequence(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 102)

    with pytest.raises(BurstMergeError, match="consecutive IDs"):
        merge_burst_safes([first, second], output_dir=tmp_path / "output")


def test_merge_supports_multiple_swaths(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101, swath="IW3")

    output = merge_burst_safes([first, second], tmp_path / "out")

    assert len(list((output / "measurement").glob("*.tiff"))) == 2


def test_cli_merge_bursts_command(tmp_path, monkeypatch, capsys):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101)
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        "sys.argv",
        ["phidown", "merge-bursts", str(first), str(second), "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as result:
        main()

    assert result.value.code == 0
    captured = capsys.readouterr()
    assert str(output_dir) in captured.out
    assert list(output_dir.glob("*.SAFE"))


def test_merge_burst_tree_accepts_raw_tiffs_and_combined_metadata(tmp_path):
    start = BASE_TIME
    product = ET.fromstring(_product_xml(burst_id=100, start=start))
    second_burst = copy.deepcopy(product.find("swathTiming/burstList/burst"))
    second_burst.find("burstId").text = "101"
    second_start = start + timedelta(seconds=2)
    second_burst.find("azimuthTime").text = second_start.isoformat().replace("+00:00", "Z")
    second_burst.find("sensingTime").text = second_burst.find("azimuthTime").text
    burst_list = product.find("swathTiming/burstList")
    burst_list.append(second_burst)
    burst_list.set("count", "2")
    general = ET.SubElement(product, "generalAnnotation")
    noise_list = ET.SubElement(general, "noiseList", {"count": "1"})
    ET.SubElement(noise_list, "noise").append(ET.Element("swath"))
    noise_list[0][0].text = "IW2"
    content = ET.Element("content")
    content.extend(copy.deepcopy(list(product)))
    combined = ET.Element("burst")
    ET.SubElement(combined, "manifest").append(ET.Element("XFDU"))
    metadata = ET.SubElement(combined, "metadata")
    product_wrapper = ET.SubElement(metadata, "product")
    ET.SubElement(product_wrapper, "swath").text = "IW2"
    ET.SubElement(product_wrapper, "polarisation").text = "VV"
    product_wrapper.append(content)
    noise_wrapper = ET.SubElement(metadata, "noise")
    ET.SubElement(noise_wrapper, "swath").text = "IW2"
    ET.SubElement(noise_wrapper, "polarisation").text = "VV"
    noise_content = ET.SubElement(noise_wrapper, "content")
    ET.SubElement(noise_content, "adsHeader")
    ET.SubElement(noise_content, "noiseRangeVectorList", {"count": "0"})
    azimuth_list = ET.SubElement(noise_content, "noiseAzimuthVectorList", {"count": "1"})
    azimuth_vector = ET.SubElement(azimuth_list, "noiseAzimuthVector")
    ET.SubElement(azimuth_vector, "swath").text = "IW2"
    ET.SubElement(azimuth_vector, "firstAzimuthLine").text = "0"
    ET.SubElement(azimuth_vector, "lastAzimuthLine").text = "3"
    ET.SubElement(azimuth_vector, "line", {"count": "4"}).text = "0 1 2 3"
    ET.SubElement(azimuth_vector, "noiseAzimuthLut", {"count": "4"}).text = "1.0 2.0 3.0 4.0"
    metadata_path = tmp_path / "combined.xml"
    ET.ElementTree(combined).write(metadata_path, encoding="utf-8", xml_declaration=True)

    data_paths = []
    for index in (0, 1):
        data_path = tmp_path / f"burst-{index}.tiff"
        tifffile.imwrite(
            data_path,
            np.full((2, 3, 2), index + 1, dtype=np.int16),
            metadata=None,
            compression=None,
            rowsperstrip=1,
            photometric="minisblack",
            planarconfig="contig",
        )
        data_paths.append(data_path)
    tree = {
        "S1A_IW_SLC__1SDV_20240102T030405_20240102T030406_123456_000789_ABCD": {
            "IW2": {
                "VV": {
                    "0": {"DATA": str(data_paths[0]), "METADATA": str(metadata_path)},
                    "1": {"DATA": str(data_paths[1]), "METADATA": str(metadata_path)},
                }
            }
        }
    }
    tree_path = tmp_path / "slc-tree.json"
    tree_path.write_text(json.dumps(tree), encoding="utf-8")

    output = merge_burst_safes([tree_path], tmp_path / "out")

    merged = tifffile.imread(next((output / "measurement").glob("*.tiff")))
    assert merged.shape == (4, 3)
    assert np.all(merged[:2] == 1 + 1j)
    assert np.all(merged[2:] == 2 + 2j)
    noise_files = list((output / "annotation" / "calibration").glob("noise-*.xml"))
    assert len(noise_files) == 1
    noise_root = ET.parse(noise_files[0]).getroot()
    assert [child.tag for child in noise_root][:3] == [
        "adsHeader",
        "noiseRangeVectorList",
        "noiseAzimuthVectorList",
    ]
    vectors = noise_root.find("noiseAzimuthVectorList")
    assert vectors is not None and [item.findtext("line") for item in vectors] == ["0 1", "2 3"]
    assert (output / "support" / "s1-level-1-product.xsd").is_file()


def _grid_record(lines, burst_lines):
    product = ET.fromstring(
        "<product><geolocationGrid><geolocationGridPointList>"
        + "".join(
            f"<geolocationGridPoint><line>{line}</line><pixel>{pixel}</pixel>"
            "<latitude>1</latitude><longitude>2</longitude><height>3</height></geolocationGridPoint>"
            for line in lines
            for pixel in (0, 10)
        )
        + "</geolocationGridPointList></geolocationGrid></product>"
    )
    return SimpleNamespace(product=product, lines=burst_lines)


def test_merged_grid_has_one_set_of_points_bounding_the_image():
    """CDSE burst grids repeat the slice grid relative to each burst."""
    group = [_grid_record([0, 100, 200, 300, 399], 100), _grid_record([-100, 0, 100, 200, 299], 100)]
    rows = sorted(int(point.findtext("line")) for point in _merged_grid_points(group))
    assert rows == [0, 0, 100, 100, 200, 200]
    assert len(_measurement_gcps(group)) == 6


def test_merged_grid_of_later_bursts_starts_at_image_line_zero():
    group = [_grid_record([-100, 0, 100, 200, 299], 100)]
    assert sorted({int(point.findtext("line")) for point in _merged_grid_points(group)}) == [0, 100]
    assert _parent_first_line(group[0]) == 100


def _noise_vector():
    return ET.fromstring(
        "<noiseAzimuthVector><firstAzimuthLine>0</firstAzimuthLine><lastAzimuthLine>400</lastAzimuthLine>"
        '<line count="5">0 100 200 300 400</line><noiseAzimuthLut count="5">1 2 3 4 5</noiseAzimuthLut></noiseAzimuthVector>'
    )


def test_noise_vector_of_first_bursts_is_cut_at_image_end():
    vector = _noise_vector()
    assert _rebase_noise_azimuth_vector(vector, 0, 201)
    assert vector.findtext("line") == "0 100 200"
    assert vector.findtext("noiseAzimuthLut") == "1 2 3"
    assert vector.findtext("lastAzimuthLine") == "200"


def test_noise_vector_of_later_bursts_is_shifted_and_interpolated():
    vector = _noise_vector()
    assert _rebase_noise_azimuth_vector(vector, -150, 100)
    assert vector.findtext("line") == "0 50 99"
    assert [float(value) for value in vector.findtext("noiseAzimuthLut").split()] == pytest.approx([2.5, 3.0, 3.49])
    assert vector.findtext("firstAzimuthLine") == "0"
    assert vector.findtext("lastAzimuthLine") == "99"


def test_merge_accepts_a_folder_of_burst_zip_archives(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    archives = tmp_path / "archives"
    archives.mkdir()
    for ordinal, burst_id in enumerate((1001, 1002), start=1):
        safe = _make_burst_safe(source, ordinal, burst_id, start=BASE_TIME + timedelta(seconds=ordinal))
        with zipfile.ZipFile(archives / f"{safe.stem}.zip", "w") as archive:
            for item in safe.rglob("*"):
                if item.is_file():
                    archive.write(item, item.relative_to(source))

    output = merge_burst_safes([archives], tmp_path / "out")

    assert (output / "manifest.safe").exists()
    assert "_000315_" in output.name  # missionDataTakeId 789 in hex.


def test_merged_manifest_describes_the_assembled_product(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100, start=BASE_TIME)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101, start=BASE_TIME + timedelta(seconds=2))

    output = merge_burst_safes([first, second], tmp_path / "output")

    manifest = (output / "manifest.safe").read_text()
    assert 'ID="s1Level1ProductSchema"' in manifest and "./support/s1-level-1-product.xsd" in manifest
    assert 'xmlns:xfdu="urn:ccsds:schema:xfdu:1"' in manifest and "ns0:" not in manifest
    assert next((output / "measurement").glob("*.tiff")).name.endswith("-000315-001.tiff")


def test_manifest_general_information_is_marked_assembled():
    general = ET.fromstring(
        "<g><productComposition>Slice</productComposition><sliceProductFlag>true</sliceProductFlag>"
        "<sliceNumber>11</sliceNumber><totalSlices>11</totalSlices></g>"
    )
    _mark_manifest_assembled(general)
    assert general.findtext("productComposition") == "Assembled"
    assert general.findtext("sliceProductFlag") == "false"
    assert general.find("sliceNumber") is None and general.find("totalSlices") is None


def test_rfi_reports_of_absent_bursts_are_removed():
    burst_list = "".join(f"<burst><azimuthTime>{time}</azimuthTime></burst>" for time in ("t1", "t2"))
    record = SimpleNamespace(
        product=ET.fromstring(f"<product><swathTiming><burstList>{burst_list}</burstList></swathTiming></product>")
    )
    rfi = ET.fromstring(
        '<rfi><rfiBurstReportList count="3">'
        + "".join(f"<rfiBurstReport><azimuthTime>{time}</azimuthTime></rfiBurstReport>" for time in ("t0", "t1", "t2"))
        + "</rfiBurstReportList></rfi>"
    )
    _keep_rfi_reports_of_bursts(rfi, [record])
    assert rfi.find("rfiBurstReportList").get("count") == "2"


def test_merge_rejects_bursts_from_different_datatakes(tmp_path):
    first = _make_burst_safe(tmp_path / "inputs", 1, 100, start=BASE_TIME)
    second = _make_burst_safe(tmp_path / "inputs", 2, 101, start=BASE_TIME + timedelta(seconds=2))
    annotation = next((second / "annotation").glob("*.xml"))
    annotation.write_text(annotation.read_text().replace("<missionDataTakeId>789<", "<missionDataTakeId>790<"))
    with pytest.raises(BurstMergeError, match="same datatake"):
        merge_burst_safes([first, second], tmp_path / "output")


def test_manifest_lists_only_polarisations_in_the_product():
    general = ET.fromstring(
        "<g><transmitterReceiverPolarisation>VV</transmitterReceiverPolarisation>"
        "<transmitterReceiverPolarisation>VH</transmitterReceiverPolarisation></g>"
    )
    _mark_manifest_assembled(general, ["VV"])
    assert [item.text for item in general] == ["VV"]


def test_footprint_uses_merged_image_corners_latitude_first():
    product = ET.fromstring(
        "<product><geolocationGrid><geolocationGridPointList>"
        + "".join(
            f"<geolocationGridPoint><line>{line}</line><pixel>{pixel}</pixel>"
            f"<latitude>{-26 - line / 100}</latitude><longitude>{30 + pixel}</longitude></geolocationGridPoint>"
            for line in (0, 100, 200)
            for pixel in (0, 1)
        )
        + "</geolocationGridPointList></geolocationGrid></product>"
    )
    corners = _group_footprint([SimpleNamespace(product=product, lines=100)])
    assert sorted(corners) == [(30.0, -27.0), (30.0, -26.0), (31.0, -27.0), (31.0, -26.0)]
    assert _footprint_string([(30.0, -26.0)]) == "-26.000000,30.000000"


def test_rfi_reports_are_combined_across_parent_slices():
    burst_list = "".join(f"<burst><azimuthTime>{time}</azimuthTime></burst>" for time in ("t1", "t2"))
    record = SimpleNamespace(
        product=ET.fromstring(f"<product><swathTiming><burstList>{burst_list}</burstList></swathTiming></product>")
    )

    def rfi(*times):
        reports = "".join(f"<rfiBurstReport><azimuthTime>{time}</azimuthTime></rfiBurstReport>" for time in times)
        return ET.fromstring(f"<rfi><rfiBurstReportList>{reports}</rfiBurstReportList></rfi>")

    output = rfi("t0", "t1")
    _keep_rfi_reports_of_bursts(output, [record], [rfi("t1", "t2", "t3")])
    assert [item.findtext("azimuthTime") for item in output.find("rfiBurstReportList")] == ["t1", "t2"]
