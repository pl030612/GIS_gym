## 單元8：F 函數與空間隨機性檢定

#### 作業說明

##### F(d) 實作：參考研讀論文針對捷運站與商家的分析過程與圖表呈現方式，進行台北市公私立國小與速食店之間的空間分析。

#### 分析台北市學校與速食店的空間分布模式（F 函數）

##### 匯入學校與速食店點位資料，設定觀測窗口並轉換為 ppp 格式

```{r}
library(sf)
library(spatstat.geom)
library(spatstat.explore)
library(spatstat.random)
library(ggplot2)

setwd("C:/Users/User/Downloads/20260228")

school_sf <- st_read("school.shp", options = "ENCODING=BIG5")
fastfood_sf <- st_read("Tpe_Fastfood.shp", options = "ENCODING=BIG5")

# 設定觀測窗口（取兩資料集聯集的 bounding box）
bbox_union <- st_bbox(st_union(st_geometry(school_sf), st_geometry(fastfood_sf)))
W <- as.owin(c(bbox_union["xmin"], bbox_union["xmax"], bbox_union["ymin"], bbox_union["ymax"]))

school_ppp <- as.ppp(st_coordinates(school_sf), W = W)
fastfood_ppp <- as.ppp(st_coordinates(fastfood_sf), W = W)
```

##### 以隨機點對學校點位的最近距離計算 F(d)，並用 Monte Carlo 模擬建立信賴區間

```{r}
set.seed(123)
n_random <- school_ppp$n
random_ppp <- runifpoint(n_random, win = W)

# 計算 random_ppp 到 school_ppp 的最近距離（F 函數）
nn_dists <- nncross(random_ppp, school_ppp)$dist
F_empirical <- ecdf(nn_dists)
d_seq <- seq(0, max(nn_dists), length.out = 100)

# Monte Carlo 模擬（99 次）建立信賴區間
r <- 99
sim_dists <- matrix(NA, nrow = r, ncol = length(d_seq))
for (i in 1:r) {
  sim_points <- runifpoint(n_random, win = W)
  sim_dist <- nncross(sim_points, school_ppp)$dist
  sim_ecdf <- ecdf(sim_dist)
  sim_dists[i, ] <- sim_ecdf(d_seq)
}

envelope_upper <- apply(sim_dists, 2, max)
envelope_lower <- apply(sim_dists, 2, min)
empirical_vals <- F_empirical(d_seq)

# 繪製 F(d) 分布與模擬信賴區間
plot(d_seq, empirical_vals, type = "l", col = "blue", lwd = 2,
     xlab = "Distance d (meters)", ylab = "F(d)",
     main = "F(d) Distribution with Simulation Envelope")
lines(d_seq, envelope_upper, col = "red", lty = 2)
lines(d_seq, envelope_lower, col = "red", lty = 2)
legend("bottomright", legend = c("F(d)", "Simulation Envelope"),
       col = c("blue", "red"), lty = c(1, 2), lwd = 2)
```
