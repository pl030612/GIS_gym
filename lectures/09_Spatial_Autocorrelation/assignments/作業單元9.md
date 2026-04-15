## 單元9：空間自相關分析（Spatial Autocorrelation）

#### 作業說明
##### 以 Contiguity 定義鄰近關係，完成以下三題：
##### 1. 繪製各鄉鎮的鄰居數的直方圖。
##### 2. 找出台灣本島最多鄰居的鄉鎮是哪一個？（回答 TOWN_ID）
##### 3. 繪製台灣各鄉鎮的 1st-order 鄰居人口密度的面量圖。

#### 作業1：繪製台灣各鄉鎮的鄰居數直方圖

##### 匯入鄉鎮資料，計算人口數與人口密度，以 poly2nb 建立鄰接關係

```{r}
rm(list = ls())
library(sf)
library(tmap)
library(spdep)
library(dplyr)
library(ggplot2)
library(units)

setwd("C:/Users/User/Downloads/20260228")
tw <- st_read("Popn_TWN2.shp", options = "ENCODING=BIG5", quiet = T)
tw$pop <- tw$A0A14_CNT + tw$A15A64_CNT + tw$A65UP_CNT
tw$area <- st_area(tw) %>% set_units("km^2") %>% drop_units
tw$den <- tw$pop / tw$area

tw.c <- poly2nb(tw)
tw.cw <- nb2listw(tw.c, zero.policy = T)

n <- sapply(tw.cw$neighbours, length)
hist(n, breaks = max(n), main = "各鄉鎮的鄰居數直方圖 (Contiguity)",
     xlab = "鄰居數", ylab = "鄉鎮數", col = "skyblue", border = "white")
```

#### 作業2：找出台灣本島最多鄰居的鄉鎮

```{r}
max_index <- which(n == max(n))
cat(tw$TOWN_ID[max_index], tw$TOWN[max_index])
# 63000110 士林區
```

#### 作業3：繪製台灣各鄉鎮 1st-order 鄰居人口密度的面量圖

##### 計算每個鄉鎮的 1st-order 鄰居平均人口密度，並以 tmap 繪製面量圖

```{r}
tw$neighbor_density <- sapply(1:length(tw.c), function(i) {
  neighbors <- tw.c[[i]]
  if (length(neighbors) == 0) return(NA)
  mean(tw$den[neighbors], na.rm = TRUE)
})

tm_shape(tw) +
  tm_polygons(col = "neighbor_density", palette = "YlOrRd",
              title = "鄰居人口密度\n(人/平方公里)",
              colorNA = "grey80", border.col = "grey20", border.alpha = 0.3) +
  tm_layout(title = "各鄉鎮 1st-order 鄰居人口密度",
            legend.outside = TRUE, frame = TRUE) +
  tm_scalebar() +
  tm_compass(position = c(0.8, 0.3))
```
