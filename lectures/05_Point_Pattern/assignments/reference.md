## 單元5：人口中心分析

#### 作業說明

##### 計算各縣市人口中心點

##### 1. 產生台灣縣市邊界，並計算各縣市幾何中心

##### 2. 利用台灣鄉鎮人口加權方式，產生各縣市的人口中心點

##### 3. 比較幾何中心點與人口中心點的差異

#### 計算台灣各縣市的幾何中心與人口重心，並比較兩者差異

##### 匯入套件與讀取資料

```{r}
library(sf)
library(dplyr)
library(tmap)

county <- st_read("C:/Users/User/Downloads/20260228/Taiwan_county.shp", options = "ENCODING=UTF8")
town <- st_read("C:/Users/User/Downloads/20260228/Popn_TWN2.shp", options = "ENCODING=BIG5")
```

##### 計算各鄉鎮人口總數，並取得各鄉鎮幾何中心點的座標

```{r}
town <- town %>%
  mutate(pop = as.numeric(A0A14_CNT) + as.numeric(A15A64_CNT) + as.numeric(A65UP_CNT))

town <- town %>%
  mutate(town_centroid = st_centroid(geometry)) %>%
  mutate(x = st_coordinates(town_centroid)[, 1],
         y = st_coordinates(town_centroid)[, 2])
```

##### 以加權平均計算各縣市人口重心（人口中心），並取得各縣市的幾何中心

```{r}
pop_center <- town %>%
  st_drop_geometry() %>%
  group_by(COUNTY) %>%
  summarise(
    pop_total = sum(pop, na.rm = TRUE),
    x_pop = sum(x * pop, na.rm = TRUE) / pop_total,
    y_pop = sum(y * pop, na.rm = TRUE) / pop_total
  ) %>%
  st_as_sf(coords = c("x_pop", "y_pop"), crs = st_crs(town))

county_centroid <- county %>%
  mutate(geom_center = st_centroid(geometry))

geom_points <- county_centroid %>%
  st_as_sf() %>%
  st_set_geometry("geom_center") %>%
  select(COUNTYNAME)

pop_points <- pop_center %>%
  select(COUNTY, geometry)
```

##### 繪製地圖，以紅點標示幾何中心、藍點標示人口中心，比較兩者差異

```{r}
tmap_mode("plot")
tm_shape(county) +
  tm_borders() +
  tm_shape(geom_points) +
  tm_symbols(shape = 21, col = "red", size = 0.3) +
  tm_shape(pop_points) +
  tm_symbols(shape = 21, col = "blue", size = 0.3) +
  tm_layout(legend.outside = TRUE) +
  tm_add_legend(type = "symbol",
                labels = c("幾何中心", "人口中心"),
                col = c("red", "blue"),
                title = "中心點")
```
