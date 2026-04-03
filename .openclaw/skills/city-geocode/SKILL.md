---
name: city-geocode
description: 根据城市名查询经纬度（调用 OpenStreetMap Nominatim 三方 API）。
---

# city-geocode

根据城市名称查询经纬度信息。

## 功能

- 输入城市名
- 调用三方 API：`https://nominatim.openstreetmap.org/search?q=<城市>&format=json`
- 输出首条匹配的经纬度，仅含 `lat` 和 `long`

## 使用方法

```bash
{baseDir}/scripts/get_city_geocode.sh Tokyo
{baseDir}/scripts/get_city_geocode.sh "New York"
{baseDir}/scripts/get_city_geocode.sh "上海"
```

## 返回示例

```json
{
  "lat": "35.6768601",
  "long": "139.7638947"
}
```

## 注意事项

- 这是公用 skill，可被多个 agent 复用。
- 仅用于地理编码查询，不包含路线规划或地图渲染。
- 请避免高频请求，遵守三方 API 使用规范。
