import argparse
import copy
import json
import math


def rad2deg(rad):
    return rad * 180 / math.pi


def load_marzipano_data_js(f):
    data_js = f.read()
    assert data_js.startswith(b"var APP_DATA = {")
    assert data_js.endswith(b"};\n")
    
    data_js = data_js[len(b"var APP_DATA = "):-len(b"};\n")] + b"}"
    return json.loads(data_js)


def convert(args):
    data = load_marzipano_data_js(args.datajs)
    
    mapping = {}
    if args.mapfile:
        mapping = json.loads(args.mapfile.read())
    
    scenes = data["scenes"]
    
    out = copy.deepcopy(PANNELLUM_DATA_TEMPLATE)
    
    for scene in scenes:
        mapped_id = mapping.get(scene["id"], {}).get("_id", scene["id"])
        out["scenes"][mapped_id] = {
            "title": mapped_id,
            "panorama": "panoramas/" + mapped_id + ".jpg",
            "yaw": rad2deg(scene["initialViewParameters"]["yaw"]),
            "pitch": rad2deg(scene["initialViewParameters"]["pitch"]),
            "hotSpots": []
        }
        out["scenes"][mapped_id].update(mapping.get(scene["id"], {}))
        
        for hotspot in scene.get("linkHotspots", []):
            mapped_target_id = mapping.get(hotspot["target"], {}).get("_id", hotspot["target"])
            out["scenes"][mapped_id]["hotSpots"].append({
                "type": "scene",
                "yaw": rad2deg(hotspot["yaw"]),
                "pitch": -rad2deg(hotspot["pitch"]),
                "text": mapped_target_id, 
                "sceneId": mapped_target_id,
                "targetYaw": "sameAzimuth"
            })
            
        for hotspot in scene.get("infoHotspots", []):
            out["scenes"][mapped_id]["hotSpots"].append({
                "type": "info",
                "yaw": rad2deg(hotspot["yaw"]),
                "pitch": -rad2deg(hotspot["pitch"]),
                "text": f"<b>{hotspot['title']}</b><br>{hotspot['text']}"
            })

    # set first scene as default - cpython preserves insertion order in dictionaries
    out["default"]["firstScene"] = next(iter(out["scenes"].keys()))

    # fix scene link names
    for sid, scene in out["scenes"].items():
        for hotspot in scene["hotSpots"]:
            if hotspot["type"] == "scene":
                hotspot["text"] = out["scenes"][hotspot["sceneId"]]["title"]

    if not args.plain:
        print(PANNELLUM_HTML_TEMPLATE.format(json.dumps(out, indent=4)))
    else:
        print(json.dumps(out, indent=4))


def dump(args):
    data = load_marzipano_data_js(args.datajs)

    scenes = data["scenes"]
    out = {}

    for scene in scenes:
        out[scene["id"]] = {
          "_id": scene["id"],
          "title": scene["name"]
        }

    print(json.dumps(out, indent=4))


PANNELLUM_DATA_TEMPLATE = {   
    "default": {
        "firstScene": None,
        "author": "author",
        "sceneFadeDuration": 1,
        "compass": True
    },
    "scenes": {}
}

PANNELLUM_HTML_TEMPLATE = """<!DOCTYPE HTML>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tour</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pannellum@2.5.7/build/pannellum.css"/>
    <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/pannellum@2.5.7/build/pannellum.js"></script>
    <style>
    html, body {{ 
        margin: 0; 
        padding: 0; 
    }}
    #panorama {{
        width: 100vw;
        height: 100vh;
    }}
    </style>
</head>
<body>

<div id="panorama"></div>
<script>
pannellum.viewer('panorama', {}
);
</script>

</body>
</html>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    parser_convert = subparsers.add_parser("convert", help="parse marzipano data.js file into pannellum format")
    parser_convert.add_argument("datajs", type=argparse.FileType('rb'), help="marzipano data.js file")
    parser_convert.add_argument("--plain", "-p", action="store_true", help="output only json, no html")
    parser_convert.add_argument("--mapfile", "-m", type=argparse.FileType('rb'), help="mapping file for scene parameters")
    parser_convert.set_defaults(func=convert)

    parser_dump = subparsers.add_parser("dump", help="dump mapfile for use with convert command to rename scenes and update other parameters like north")
    parser_dump.add_argument("datajs", type=argparse.FileType('rb'), help="marzipano data.js file")
    parser_dump.set_defaults(func=dump)

    args = parser.parse_args()
    args.func(args)
