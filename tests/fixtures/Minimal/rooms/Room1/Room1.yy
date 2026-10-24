{
  "$GMRoom": "v1",
  "%Name": "Room1",
  "creationCodeFile": "",
  "inheritCode": false,
  "inheritCreationOrder": false,
  "inheritLayers": false,
  "instanceCreationOrder": [
    {
      "name": "inst_EBAF606B",
      "path": "rooms/Room1/Room1.yy"
    },
    {
      "name": "inst_D2D77C4A",
      "path": "rooms/Room1/Room1.yy"
    }
  ],
  "isDnd": false,
  "layers": [
    {
      "$GMRInstanceLayer": "",
      "%Name": "Instances",
      "depth": 0,
      "effectEnabled": true,
      "effectType": null,
      "gridX": 32,
      "gridY": 32,
      "hierarchyFrozen": false,
      "inheritLayerDepth": false,
      "inheritLayerSettings": false,
      "inheritSubLayers": true,
      "inheritVisibility": true,
      "instances": [
        {
          "$GMRInstance": "v4",
          "%Name": "inst_EBAF606B",
          "colour": 4294967295,
          "frozen": false,
          "hasCreationCode": false,
          "ignore": false,
          "imageIndex": 0,
          "imageSpeed": 1.0,
          "inheritCode": false,
          "inheritedItemId": null,
          "inheritItemSettings": false,
          "isDnd": false,
          "name": "inst_EBAF606B",
          "objectId": {
            "name": "obj_player",
            "path": "objects/obj_player/obj_player.yy"
          },
          "properties": [],
          "resourceType": "GMRInstance",
          "resourceVersion": "2.0",
          "rotation": 0.0,
          "scaleX": 1.0,
          "scaleY": 1.0,
          "x": 64.0,
          "y": 64.0
        },
        {
          "$GMRInstance": "v4",
          "%Name": "inst_D2D77C4A",
          "colour": 4294967295,
          "frozen": false,
          "hasCreationCode": false,
          "ignore": false,
          "imageIndex": 0,
          "imageSpeed": 1.0,
          "inheritCode": false,
          "inheritedItemId": null,
          "inheritItemSettings": false,
          "isDnd": false,
          "name": "inst_D2D77C4A",
          "objectId": {
            "name": "obj_wall",
            "path": "objects/obj_wall/obj_wall.yy"
          },
          "properties": [],
          "resourceType": "GMRInstance",
          "resourceVersion": "2.0",
          "rotation": 0.0,
          "scaleX": 1.0,
          "scaleY": 1.0,
          "x": 128.0,
          "y": 64.0
        }
      ],
      "layers": [],
      "name": "Instances",
      "properties": [],
      "resourceType": "GMRInstanceLayer",
      "resourceVersion": "2.0",
      "userdefinedDepth": false,
      "visible": true
    },
    {
      "$GMRTileLayer": "",
      "%Name": "Tiles_Collision",
      "depth": 100,
      "effectEnabled": true,
      "effectType": null,
      "gridX": 16,
      "gridY": 16,
      "hierarchyFrozen": false,
      "inheritLayerDepth": false,
      "inheritLayerSettings": false,
      "inheritSubLayers": true,
      "inheritVisibility": true,
      "layers": [],
      "name": "Tiles_Collision",
      "properties": [],
      "resourceType": "GMRTileLayer",
      "resourceVersion": "2.0",
      "tiles": {
        "SerialiseHeight": 34,
        "SerialiseWidth": 60,
        "TileCompressedData": [
          -4,
          1,
          -2036,
          0
        ],
        "TileDataFormat": 1
      },
      "tilesetId": {
        "name": "ts_main",
        "path": "tilesets/ts_main/ts_main.yy"
      },
      "userdefinedDepth": true,
      "visible": true,
      "x": 0,
      "y": 0
    },
    {
      "$GMRBackgroundLayer": "",
      "%Name": "Background",
      "animationFPS": 15.0,
      "animationSpeedType": 0,
      "colour": 4280427042,
      "depth": 200,
      "effectEnabled": true,
      "effectType": null,
      "gridX": 32,
      "gridY": 32,
      "hierarchyFrozen": false,
      "hspeed": 0.0,
      "htiled": false,
      "inheritLayerDepth": false,
      "inheritLayerSettings": false,
      "inheritSubLayers": true,
      "inheritVisibility": true,
      "layers": [],
      "name": "Background",
      "properties": [],
      "resourceType": "GMRBackgroundLayer",
      "resourceVersion": "2.0",
      "spriteId": null,
      "stretch": false,
      "userdefinedAnimFPS": false,
      "userdefinedDepth": false,
      "visible": true,
      "vspeed": 0.0,
      "vtiled": false,
      "x": 0,
      "y": 0
    }
  ],
  "name": "Room1",
  "parent": {
    "name": "Rooms",
    "path": "folders/Rooms.yy"
  },
  "parentRoom": null,
  "physicsSettings": {
    "inheritPhysicsSettings": false,
    "PhysicsWorld": false,
    "PhysicsWorldGravityX": 0.0,
    "PhysicsWorldGravityY": 10.0,
    "PhysicsWorldPixToMetres": 0.1
  },
  "resourceType": "GMRoom",
  "resourceVersion": "2.0",
  "roomSettings": {
    "Height": 540,
    "inheritRoomSettings": false,
    "persistent": false,
    "Width": 960
  },
  "sequenceId": null,
  "views": [
    {
      "hborder": 32,
      "hport": 540,
      "hspeed": -1,
      "hview": 540,
      "inherit": false,
      "objectId": null,
      "vborder": 32,
      "visible": true,
      "vspeed": -1,
      "wport": 960,
      "wview": 960,
      "xport": 0,
      "xview": 0,
      "yport": 0,
      "yview": 0
    }
  ],
  "viewSettings": {
    "clearDisplayBuffer": true,
    "clearViewBackground": false,
    "enableViews": true,
    "inheritViewSettings": false
  },
  "volume": 1.0
}
