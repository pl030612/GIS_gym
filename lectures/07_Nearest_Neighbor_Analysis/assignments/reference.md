## 單元7：最近鄰分析（NNA）與 G 函數

#### 作業說明

##### 利用課堂提供的資料，利用 Nearest-Neighbor Distances，比較任兩個縣市信仰「觀音菩薩」的村落型祭祀圈的寺廟空間群聚特性，並討論之。

##### 分析內容須包含：

##### - Nearest Neighbor Analysis（NNA）

##### - K-order Nearest Neighbor Distances (or Indices)

##### - G(d) Function

#### 分析台北縣與高雄縣的村落型觀音廟宇空間分布特性

##### 匯入台灣媽祖祭祀圈廟宇點位資料與鄉鎮行政區底圖

```{r}
library(sf)
library(tmap)
library(aspace)
library(tidyverse)

temple <- st_read("C:/Users/User/Downloads/20260228/Tempcycle_twd97.shp")
village_g <- st_read("C:/Users/User/Downloads/20260228/Popn_TWN2.shp", options = "ENCODING=BIG5")

st_crs(village_g) <- st_crs(temple)

```

##### 篩選村落型觀音祭祀圈廟宇，並轉換為 spatstat ppp 格式

```{r}
library(spatstat.geom)
library(spatstat.explore)
library(spatstat.random)
library(ggplot2)

village_g <- temple |>
  filter(grepl("觀音|觀世音", 主祭神祇), 祭祀圈層級 == "村落型") |>
  mutate(COUNTY = substr(COUNTYNAME, 1, 5))

two_cty <- c("台北縣", "高雄縣")
pts <- lapply(two_cty, function(cty) {
  village_g |> filter(COUNTYNAME == cty) |> st_transform(3826)
})
names(pts) <- two_cty

ppp_list <- lapply(pts, function(x) {
  coords <- st_coordinates(x)
  win <- owin(xrange = range(coords[, 1]), yrange = range(coords[, 2]))
  ppp(coords[, 1], coords[, 2], window = win)
})
names(ppp_list) <- two_cty
```

##### 計算 NNI（最近鄰指數）與 Z 分數，p 值均為 0，兩縣廟宇皆呈顯著群聚

```{r}
nni_results <- lapply(seq_along(ppp_list), function(i) {
  p <- ppp_list[[i]]
  nnd <- nndist(p)
  obs_mean <- mean(nnd)
  area <- area.owin(p$window)
  n <- p$n
  exp_mean <- 1 / (2 * sqrt(n / area))
  nni <- obs_mean / exp_mean
  z_score <- (obs_mean - exp_mean) / (sqrt(0.26 / n))
  data.frame(
    County = names(ppp_list)[i],
    NNI = nni,
    Z_score = z_score,
    Observed_mean = obs_mean,
    Expected_mean = exp_mean,
    p_value = 2 * pnorm(-abs(z_score))
  )
})

nni_summary <- do.call(rbind, nni_results)
print(nni_summary)
#   County       NNI   Z_score Observed_mean Expected_mean p_value
# 1 台北縣 0.6970385 -11259.30      2641.784      3790.012       0
# 2 高雄縣 0.5389046 -24039.23      1724.661      3200.309       0
```

##### 以 Monte Carlo 模擬進行 NNA 與 K-order NNA 的信賴區間估計

```{r}
# Monte Carlo NNA 模擬繪圖函式
plot_nna_simulation <- function(ppp_obj, name, nsim = 999) {
  obs_nnd <- mean(nndist(ppp_obj))
  area <- area.owin(ppp_obj$window)
  n <- ppp_obj$n
  sim_nnd_means <- replicate(nsim, {
    p_sim <- rpoispp(lambda = n / area, win = ppp_obj$window)
    mean(nndist(p_sim))
  })
  hist(sim_nnd_means, breaks = 30,
       main = paste("Monte Carlo Simulation of NNA:\n", name),
       xlab = "Distance (m)", col = "grey", border = "white",
       xlim = range(c(sim_nnd_means, obs_nnd)))
  abline(v = obs_nnd, col = "red", lwd = 2)
  abline(v = quantile(sim_nnd_means, c(0.025, 0.975)), col = "blue", lty = 2)
}

par(mfrow = c(1, length(ppp_list)))
for (i in seq_along(ppp_list)) {
  plot_nna_simulation(ppp_list[[i]], names(ppp_list)[i])
}

# K-order NNA 模擬繪圖函式
plot_k_order_nnd <- function(ppp_obj, name, max_k = 4, nsim = 199) {
  area <- area.owin(ppp_obj$window)
  n <- ppp_obj$n
  obs_k_nnd <- sapply(1:max_k, function(k) mean(nndist(ppp_obj, k = k)))
  sim_k_nnd <- replicate(nsim, {
    sim_p <- rpoispp(lambda = n / area, win = ppp_obj$window)
    sapply(1:max_k, function(k) mean(nndist(sim_p, k = k)))
  })
  mean_sim <- apply(sim_k_nnd, 1, mean)
  ci <- apply(sim_k_nnd, 1, quantile, probs = c(0.025, 0.975))
  plot(1:max_k, obs_k_nnd, type = "l", col = "red", lwd = 2,
       ylim = range(c(obs_k_nnd, ci)),
       xlab = "order", ylab = "mean nearest distance (m)",
       main = paste("Monte Carlo Simulation of\nK-order NNI:", name))
  lines(1:max_k, ci[1, ], col = "blue", lty = 2)
  lines(1:max_k, ci[2, ], col = "blue", lty = 2)
}

par(mfrow = c(1, length(ppp_list)))
for (i in seq_along(ppp_list)) {
  plot_k_order_nnd(ppp_list[[i]], names(ppp_list)[i])
}
```

##### 繪製 G 函數，比較台北縣與高雄縣的群聚特性：高雄縣 G(d) 曲線提早上升，代表較強群聚

```{r}
# G 函數 Monte Carlo 模擬
plot_g_function_with_simulation <- function(ppp_obj, name, nsim = 99) {
  set.seed(123)
  env <- envelope(ppp_obj, Gest, nsim = nsim, correction = "km", savefuns = TRUE)
  plot(env,
       main = paste("Monte Carlo Simulation of\nG function:", name),
       xlab = "distance(m)", ylab = "G(d)", legend = FALSE, col = "gray")
  lines(env$r, env$obs, col = "red", lwd = 2)
}

par(mfrow = c(1, length(ppp_list)))
for (i in seq_along(ppp_list)) {
  plot_g_function_with_simulation(ppp_list[[i]], names(ppp_list)[i])
}

# 比較兩縣 G 函數
compare_g_function <- function(ppp_list, city_names) {
  g_list <- lapply(ppp_list, function(p) Gest(p, correction = "km"))
  plot(g_list[[1]]$r, g_list[[1]]$km, type = "s", col = "blue", lwd = 2,
       xlab = "distance(m)", ylab = "G(d)",
       main = paste("Comparison: Monte Carlo Simulation of G function\n",
                    city_names[1], "and", city_names[2]))
  lines(g_list[[2]]$r, g_list[[2]]$km, col = "red", lwd = 2, type = "s")
  legend("bottomright", legend = city_names, col = c("blue", "red"), lwd = 2)
}

compare_g_function(ppp_list[1:2], names(ppp_list)[1:2])
# 高雄縣 G(d) 曲線相較台北縣明顯提前上升，顯示廟宇最近鄰距離較短，群聚程度較強
```
