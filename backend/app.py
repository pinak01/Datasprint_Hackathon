# import os
# import numpy as np
# import geopandas as gpd
# from shapely.geometry import Polygon
# from dotenv import load_dotenv
# from PIL import Image   # <-- added

# from sentinelhub import (
#     SHConfig,
#     SentinelHubRequest,
#     DataCollection,
#     MimeType,
#     BBox,
#     CRS
# )

# # --- 1. LOAD SENTINEL HUB CREDENTIALS FROM .env ---
# load_dotenv()
# CLIENT_ID = os.getenv("Client_id")
# CLIENT_SECRET = os.getenv("Client_secret")

# if not CLIENT_ID or not CLIENT_SECRET:
#     raise ValueError("Missing SH_CLIENT_ID or SH_CLIENT_SECRET in .env file")

# config = SHConfig()
# config.sh_client_id = CLIENT_ID
# config.sh_client_secret = CLIENT_SECRET

# # --- 2. DEFINE YOUR LAND POLYGON (replace with your coords) ---
# MY_LAND_GEOMETRY = {
#     "type": "Polygon",
#     "coordinates": [[[76.950903,24.521356],[76.947041,24.5155],[76.95262,24.510892],[76.954508,24.517608],[76.950903,24.521356]]]
# }


# aoi_gdf = gpd.GeoDataFrame(
#     index=[0], crs="EPSG:4326", geometry=[Polygon(MY_LAND_GEOMETRY['coordinates'][0])]
# )
# land_bbox = BBox(bbox=tuple(aoi_gdf.total_bounds), crs=CRS.WGS84)

# # --- 3. OUTPUT SETTINGS ---
# output_dir = "land_images"
# os.makedirs(output_dir, exist_ok=True)
# time_interval = ("2024-01-01", "2024-04-30")   # change as needed
# image_size = (512, 512)

# # --- 4. EVALSCRIPT ---
# evalscript_true_color = """
#     //VERSION=3
#     function setup() {
#         return {
#             input: [{ bands: ["B04", "B03", "B02"] }],
#             output: { bands: 3 }
#         };
#     }
#     function evaluatePixel(sample) {
#         return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
#     }
# """

# # --- 5. REQUEST IMAGE ---
# print("Requesting image for your land...")

# request = SentinelHubRequest(
#     evalscript=evalscript_true_color,
#     input_data=[
#         SentinelHubRequest.input_data(
#             data_collection=DataCollection.SENTINEL2_L1C,
#             time_interval=time_interval,
#             mosaicking_order="leastCC"
#         )
#     ],
#     responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
#     bbox=land_bbox,
#     size=image_size,
#     config=config
# )

# try:
#     image_array = request.get_data()[0]  # numpy array (H, W, 3)

#     if np.mean(image_array) > 10:
#         filename = os.path.join(output_dir, "my_land.png")
#         img = Image.fromarray(image_array.astype(np.uint8))  # save as PNG
#         img.save(filename)
#         print(f"✅ Image saved: {filename}")
#     else:
#         print("⚪ No valid data (area might be dark/cloudy). Try another date.")

# except Exception as e:
#     print(f"❌ Error fetching image: {e}")



import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from dotenv import load_dotenv
from PIL import Image
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS   
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    BBox,
    CRS
)

# --- 1. Flask App ---
app = Flask(__name__)
CORS(app) 
# --- 2. Load Sentinel Hub Credentials ---
load_dotenv()
CLIENT_ID = os.getenv("Client_id")
CLIENT_SECRET = os.getenv("Client_secret")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing Client_id or Client_secret in .env file")

config = SHConfig()
config.sh_client_id = CLIENT_ID
config.sh_client_secret = CLIENT_SECRET

# --- 3. Default settings ---
OUTPUT_DIR = "land_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)
TIME_INTERVAL = ("2024-01-01", "2024-04-30")  # adjust as needed
IMAGE_SIZE = (512, 512)

EVALSCRIPT_TRUE_COLOR = """
//VERSION=3
function setup() {
    return {
        input: [{ bands: ["B04", "B03", "B02"] }],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
}
"""

# --- 4. Route to handle coordinates from frontend ---
@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.get_json()
        if not data or "coordinates" not in data:
            return jsonify({"error": "Missing coordinates"}), 400

        coords = data["coordinates"]

        # Build polygon
        aoi_gdf = gpd.GeoDataFrame(
            index=[0],
            crs="EPSG:4326",
            geometry=[Polygon(coords)]
        )
        land_bbox = BBox(bbox=tuple(aoi_gdf.total_bounds), crs=CRS.WGS84)

        # Sentinel request
        request_sentinel = SentinelHubRequest(
            evalscript=EVALSCRIPT_TRUE_COLOR,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L1C,
                    time_interval=TIME_INTERVAL,
                    mosaicking_order="leastCC"
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
            bbox=land_bbox,
            size=IMAGE_SIZE,
            config=config
        )

        image_array = request_sentinel.get_data()[0]

        if np.mean(image_array) > 10:
            filename = os.path.join(OUTPUT_DIR, "my_land.png")
            img = Image.fromarray(image_array.astype(np.uint8))
            img.save(filename)
            return send_file(filename, mimetype="image/png")
        else:
            return jsonify({"message": "No valid data (area might be dark/cloudy). Try another date."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def home():
    return "✅ Backend is running! POST your land polygon to /submit"


if __name__ == "__main__":
    app.run(debug=True)
