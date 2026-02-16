# Custom Material Profiles

Place custom material profile JSON files in this directory.

Each file should contain a single material profile or an array of profiles.

## Example

```json
{
  "id": "custom_inconel_625",
  "name": "Inconel 625",
  "processType": "waam",
  "category": "metal",
  "description": "Nickel-chromium superalloy for high-temperature applications.",
  "properties": {
    "density": 8440.0,
    "meltTemp": 1350.0,
    "beadWidth": 4.0,
    "layerHeight": 1.5,
    "printSpeed": 7.0,
    "travelSpeed": 60.0,
    "flowRate": 1.0
  },
  "slicingDefaults": {
    "layerHeight": 1.5,
    "extrusionWidth": 4.0,
    "wallCount": 1,
    "infillDensity": 1.0,
    "infillPattern": "lines",
    "printSpeed": 7.0,
    "travelSpeed": 60.0
  }
}
```
