## 單元6：點位空間群聚分析（Quadrat Analysis）

#### 作業說明
##### 對於「祭祀圈」的定義：祭祀圈以主祭神所在的廟宇為中心，「村落型祭祀圈」的影響半徑約為 2 公里。若全台舉辦盛大媽祖繞境活動，各地信眾均從「村落型祭祀圈」之中心廟宇出發，請回答下列問題：

##### 台灣本島範圍：
##### 1. 若所有信仰媽祖的信眾皆從所屬祭祀圈之中心廟宇出發，要決定其中一間寺廟作為各地遶境團體匯流的折返點，如何使所有信眾的直線距離總和最小化？
##### 2. 承上題，若主辦單位決定改成另外搭設遶境大會中心作為匯流折返點，同樣欲使所有信眾的起終直線距離總和最小化，其中心設置的位置應於何處？（鄉鎮名稱）

##### 南部地區（嘉義、台南、高雄、屏東）範圍：
##### 3. 利用 Quadrat analysis，以 20 km × 20 km 的網格，比較信仰「媽祖」與「觀音菩薩」的寺廟的空間群聚特性，並討論之。
##### 4. 利用 Quadrat analysis，比較 20 km × 20 km vs. 50 km × 50 km 的網格，計算信仰「媽祖」寺廟的空間群聚特性的差異，並討論網格尺度對於檢定空間群聚之影響。

#### 資料準備

##### 匯入台灣媽祖祭祀圈廟宇點位資料與鄉鎮行政區底圖

```{r}
library(sf)
library(tmap)
library(aspace)
library(tidyverse)

temples <- st_read("C:/Users/User/Downloads/20260228/Taiwan_temple.shp")
towns <- st_read("C:/Users/User/Downloads/20260228/Popn_TWN2.shp", options = "ENCODING=BIG5")

st_crs(towns) <- st_crs(temples)

# 合併為縣市層級底圖
city <- towns %>%
  group_by(COUNTY_ID) %>%
  summarise(geometry = st_union(geometry))

background <- tm_shape(city) + tm_polygons(border, col = "#666666", alpha = 0) + tm_fill(col = "#F0F0F0")
temples_lyr <- tm_shape(temples) + tm_dots(col = "#B22222", size = 0.005, alpha = 0.7) + tm_layout(frame = F)

background + temples_lyr
```

### I. 台灣本島分析

#### 1. 尋找直線距離總和最小化的中心廟宇（Central Feature）

##### 使用 calc_cf() 計算 Central Feature，即使所有信眾直線距離總和最小的現有廟宇

```{r}
temple_df <- data.frame(x = temples$X_coord, y = temples$Y_coord)
central_feature <- calc_cf(id = 1, points = temple_df, verbose = FALSE)

cfx <- as.numeric(central_feature$LOCATIONS[2])
cfy <- as.numeric(central_feature$LOCATIONS[3])
cf_sf <- c(cfx, cfy) %>% st_point %>% st_sfc %>% st_sf
st_crs(cf_sf) <- st_crs(temples)

cf_layer <- tm_shape(cf_sf) +
  tm_symbols(shape = 23, col = "#1E90FF", size = 0.5, border.col = "black", border.lwd = 1)

background + temples_lyr + cf_layer

# 查詢該廟宇名稱
cf_temple <- st_join(cf_sf, temples, join = st_within)
paste(cf_temple$FULLNAME, cf_temple$NAME)
# [1] "雲林縣古坑鄉 三泰宮"
```

#### 2. 尋找使距離總和最小化的最佳新設地點（Mean Center）

##### 使用 calc_mdc() 計算 Mean Center，即在任意位置新設一點使距離總和最小

```{r}
temple_df <- data.frame(x = temples$X_coord, y = temples$Y_coord,
                        tpname = temples$NAME, god = temples$God)
md_center <- calc_mdc(id = 1, points = temple_df, verbose = FALSE)

mdx <- md_center$LOCATIONS[2]
mdy <- md_center$LOCATIONS[3]
md_sf <- c(mdx, mdy) %>% st_point %>% st_sfc %>% st_sf
st_crs(md_sf) <- st_crs(temples)

md_layer <- tm_shape(md_sf) +
  tm_symbols(shape = 21, col = "#FFD700", size = 0.4, border.col = "black", border.lwd = 1)

background + temples_lyr + cf_layer + md_layer

# 查詢所在鄉鎮
result <- st_join(md_sf, towns, join = st_within)
print(result$TOWN)
# [1] "斗六市"
```

### II. 南部地區分析（嘉義、台南、高雄、屏東）

#### 1. 媽祖與觀音菩薩廟宇的空間群聚比較（20km × 20km 網格）

##### 篩選南部地區廟宇，建立 20km × 20km 網格並計算各格廟宇數，以 VMR 檢定群聚性

```{r}
# 篩選南部地區
index <- towns$COUNTY %in% c("嘉義市", "嘉義縣", "台南縣", "臺南市", "高雄市", "高雄縣", "屏東縣", "屏東市")
twn_south <- towns[index, ]
temple_south <- st_intersection(temples, twn_south)

# 建立 20km 網格
grid <- st_make_grid(temple_south, 20000, crs = st_crs(temple_south), what = "polygons", square = TRUE)
grid_sf <- st_sf(index = 1:length(lengths(grid)), grid)
names(grid_sf) <- c("grd_id", "grid")

# 計算每格廟宇數
count_sf <- st_join(grid_sf, temple_south)
quad_sf <- summarise(group_by(count_sf, grd_id), count = length(grd_id))
grid_sf$count <- 0
grid_sf$count[quad_sf$grd_id] <- quad_sf$count

# 分別統計媽祖與觀音廟數
count_MAZU <- count_sf %>% as.data.frame() %>% filter(God == "媽祖") %>% group_by(grd_id) %>% summarise(count = n())
count_GUAN <- count_sf %>% as.data.frame() %>% filter(God == "觀音菩薩") %>% group_by(grd_id) %>% summarise(count = n())
grid_sf$countmazu <- 0
grid_sf$countguan <- 0
grid_sf$countmazu[count_MAZU$grd_id] <- count_MAZU$count
grid_sf$countguan[count_GUAN$grd_id] <- count_GUAN$count

# VMR 檢定函式
p_value_cal <- function(vec) {
  np <- length(vec)
  meanp <- mean(vec)
  varp <- var(vec)
  vmrp <- varp / meanp
  se <- sqrt(2 / (np - 1))
  t <- (vmrp - 1) / se
  pvalue <- pt(t, df = np - 1, lower.tail = F)
  return(format(pvalue, scientific = TRUE, digits = 6))
}

p_value_cal(grid_sf$countmazu)  # [1] "1.14711e-58"
p_value_cal(grid_sf$countguan)  # [1] "1.99288e-16"
# 兩者 p 值遠小於 0.05，皆呈現顯著群聚
```

#### 2. 網格尺度對群聚檢定的影響比較（20km vs. 50km）

##### 改用 50km × 50km 網格重複上述分析，比較 VMR p 值差異，討論網格尺度影響

```{r}
# 建立 50km 網格（重複上述步驟，僅改網格大小）
grid <- st_make_grid(temple_south, 50000, crs = st_crs(temple_south), what = "polygons", square = TRUE)
grid_sf <- st_sf(index = 1:length(lengths(grid)), grid)
names(grid_sf) <- c("grd_id", "grid")

count_sf <- st_join(grid_sf, temple_south)
quad_sf <- summarise(group_by(count_sf, grd_id), count = length(grd_id))
grid_sf$count <- 0
grid_sf$count[quad_sf$grd_id] <- quad_sf$count

count_MAZU <- count_sf %>% as.data.frame() %>% filter(God == "媽祖") %>% group_by(grd_id) %>% summarise(count = n())
count_GUAN <- count_sf %>% as.data.frame() %>% filter(God == "觀音菩薩") %>% group_by(grd_id) %>% summarise(count = n())
grid_sf$countmazu <- 0
grid_sf$countguan <- 0
grid_sf$countmazu[count_MAZU$grd_id] <- count_MAZU$count
grid_sf$countguan[count_GUAN$grd_id] <- count_GUAN$count

p_value_cal(grid_sf$countmazu)  # [1] "3.54709e-14"
p_value_cal(grid_sf$countguan)  # [1] "3.11831e-07"
# 方格變大後 p 值增大，代表方格尺度越大，格間數量落差縮小，變異數相對減小，群聚程度較不明顯
```