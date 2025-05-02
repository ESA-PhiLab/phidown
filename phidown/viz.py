# This script extracts coordinates from a KML file and plots them on a map using Folium.
# Import necessary libraries
import xml.etree.ElementTree as ET
import folium
import argparse


def plot_kml_coordinates(kml_file, output_html="map_overlay.html"):
    """
    Extracts coordinates from a KML file and plots them on a map.

    Args:
        kml_file (str): Path to the KML file.
        output_html (str): Path to save the generated HTML map.
    """
    # Define the namespace for the KML file
    namespace = {
        "gx": "http://www.google.com/kml/ext/2.2",
        "kml": "http://www.opengis.net/kml/2.2"
    }

    # Parse the KML file
    tree = ET.parse(kml_file)
    root = tree.getroot()

    # Extract coordinates from the <gx:LatLonQuad> tag
    coordinates_text = root.find(".//gx:LatLonQuad/coordinates", namespace).text.strip()
    # Split the coordinates and convert them to a list of [latitude, longitude]
    coordinates = [
        [float(coord.split(",")[1]), float(coord.split(",")[0])]
        for coord in coordinates_text.split()
    ]

    # Close the polygon by repeating the first coordinate
    coordinates.append(coordinates[0])

    # Create a map centered around the first coordinate
    m = folium.Map(location=coordinates[0], zoom_start=10)

    # Add the polygon to the map
    folium.Polygon(
        locations=coordinates,
        color="blue",
        weight=2,
        fill=True,
        fill_color="black",
        fill_opacity=0.2
    ).add_to(m)

    # Save the map to an HTML file
    m.save(output_html)
    print(f"Map has been saved as '{output_html}'. Open it in a browser to view.")
    return m


if __name__ == "__main__":

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Plot coordinates from a KML file on a map.")
    parser.add_argument("-kml", type=str, help="Path to the KML file.")
    parser.add_argument(
        "--output_html",
        type=str,
        default="map_overlay.html",
        help="Path to save the generated HTML map (default: map_overlay.html)."
    )

    # Parse arguments
    args = parser.parse_args()

    # Call the function with the provided arguments
    plot_kml_coordinates(args.kml, args.output_html)
