

# 環境設定與載入資料 -------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(tmap) #互動式及靜態地圖繪製
library(cartography) #支援製作點子圖
library(classInt) #用於生成分級資料


rm(list=ls())
setwd("C:/Data/CH2")
temple = st_read(dsn = 'Taiwan_temple.shp')
town = st_read(dsn = 'Taiwan_town.shp')
county = st_read(dsn = 'Taiwan_county.shp')
windowsFonts(JH = windowsFont("微軟正黑體"))
tmap_mode('view') #tamp切換為互動式（靜態則將參數設為'plot'）



# 2-1實際點位資料的空間分布 -------------------------------------------------------

##1.資料篩選
mazhou = subset(temple, God == "媽祖")

##2.繪製媽祖廟宇分布
tm_shape(county) +  #指定第一個圖層
    tm_polygons(col = 'black') + #底圖為縣市面圖形
    tm_shape(mazhou) +  #指定第二個圖層
    tm_symbols(size = 0.3, shape = 21, fill = "red", col = NA) #疊上篩選出的點資料



# 2-2空間統計資料的分布－點子圖(鄉鎮)  ----------------------------------------------

##1.計算各鄉鎮媽祖廟宇數量
town$mazhou_count = lengths(st_contains(town, mazhou))

##2.繪製底圖
par(mar = c(1, 1, 1, 1))  # 下、左、上、右邊界
plot(st_geometry(county), #縣市圖層作為統一的底圖
     col = 'lightgreen',
     bg = "lightblue1")

##3.繪製點子圖
dotDensityLayer(
    town, #帶入的資料
    var = 'mazhou_count', #代表變數，每個區域的媽祖廟數量
    n = 1, #1個點代表1間廟
    cex = 1.2, #點的縮放
    pch = 20, #點的形狀
    col = 'red', #點的顏色
    legend.txt = '1點代表1間廟', #圖例文字
    legend.cex = 1, #圖例大小
    legend.pos = 'bottomleft', #圖例放在左下角
    legend.frame = FALSE, #圖例不要有外框
    add = TRUE
)
layoutLayer(title = "台灣媽祖廟宇點子圖(鄉鎮)", #地圖標題
            north = T, #加上指北針
            postitle = "center") #標題置中






# 2-2空間統計資料的分布－點子圖(縣市) -----------------------------------------------

##1.計算各縣市媽祖廟宇數量
county$mazhou_count = lengths(st_contains(county, mazhou))

##2.繪製底圖
plot(st_geometry(county),
     col = 'lightgreen',
     bg = "lightblue1")

##3.繪製點子圖
dotDensityLayer(
    county,
    var = 'mazhou_count',
    n = 1,
    cex = 1.2,
    pch = 20,
    col = 'red',
    legend.txt = '1點代表1間廟',
    legend.cex = 1,
    legend.pos = 'bottomleft',
    legend.frame = FALSE
)
layoutLayer(title = "台灣媽祖廟宇點子圖(縣市)",
            north = T,
            postitle = "center")






# 2-3空間統計資料的分布－分級符號圖 ---------------------------------------------------

##1.繪製分級符號圖
county$mazhou_count = lengths(st_contains(county, mazhou)) #計算各縣市廟宇數量
center = st_centroid(county) #找到縣市多邊形的中心
tm_shape(county) + 
    tm_polygons(col = 'black') +
    tm_shape(center) + 
    tm_symbols('mazhou_count', fill='red', scale = 3) #符號預設圓形

##2.繪製長條圖
par(mar = c(4, 4, 2, 4), mfrow = c(2, 1)) #調整結果圖的邊界，並以上下圖呈現
barplot(county$mazhou_count, #長條圖高度依據
        names.arg = county$COUNTYNAME, #長條圖橫軸名稱
        las = 2) #將橫軸文字90°旋轉垂直顯示，並按照原始資料順序

barplot(
    sort(county$mazhou_count, decreasing = T), #按照縣市媽祖廟宇數量降冪排序
    names.arg = county$COUNTYNAME[order(county$mazhou_count, decreasing = T)],
    las = 2
) 


# 2-4空間統計資料的分布－面量圖（合適的分級方法） --------------------------------------------

##1.計算每平方公里的媽祖廟宇密度
town$mazhou_count = lengths(st_contains(town, mazhou))
town$area = as.numeric(st_area(town))
town$mazhou_density = town$mazhou_count / town$area * 10 ^ 6

##2.繪製媽祖廟宇分布密度面量圖(等量分級法)
tm_shape(town) + tm_polygons('mazhou_density', 
                             n = 7, #區分為7個級數
                             style = "quantile", #分級方法
                             palette = "BuGn") #主題色


##3.繪製媽祖廟宇分布密度面量圖(自然分級法、等量分級法、等距分級法)

windowsFonts(JH = windowsFont("微軟正黑體")) #設定字體
methods_name = c("自然分級法", "等量分級法", "等距分級法") #定義分級方法
methods = c("fisher", "quantile", "equal") #定義圖名稱
maps = list() #先為迴圈建立儲存用的空列表

for (i in 1:3) {
    #使用迴圈生成多張地圖
    map <- tm_shape(town) +
        tm_polygons(
            col = "mazhou_density",
            style = methods[i], #引入分級方法
            n = 4,
            palette = "Reds",
            title = "媽祖廟宇密度" #圖例標題
        ) +
        tm_shape(county) +
        tm_borders(col = "black") + #加上縣市圖層邊框
        tm_layout(
            fontfamily = "JH", #使用微軟正黑體
            title = methods_name[i], #設定地圖標題
            legend.format = list(digits = 2), # 設定圖例只顯示小數點後2位
        )
    maps[[i]] <- map #將每張地圖加入列表
}
tmap_arrange(maps[[1]], maps[[2]], maps[[3]]) #顯示三張並排地圖


# 2-5空間統計資料的分布－面量圖（合適的數值單位） --------------------------------------------

##1.媽祖廟宇數量
map_count = tm_shape(town) +
    tm_polygons(
        col = "mazhou_count",
        style = "fisher", #使用自然分級法
        n = 5,
        palette = "Reds",
        title = "媽祖廟宇數量"
    ) +
    tm_shape(county) +
    tm_borders(col = "black")

##2.媽祖廟宇數量等級
class = classIntervals(
    var = town$mazhou_count,
    n = 3, #分成3級
    style = "fisher", #自然分級法
    town$level = cut(
        town$mazhou_count,
        breaks = class$brks, #提取class中的分級邊界
        labels = c("Level1", "Level2", "Level3"),
        include.lowest = TRUE #包含分級的下界
    )
)
map_level = tm_shape(town) +
    tm_polygons(col = "level",
                palette = "Reds",
                title = "媽祖廟宇數量等級") +
    tm_shape(county) +
    tm_borders(col = "black")

##3.媽祖廟宇數量密度
map_density = tm_shape(town) +
    tm_polygons(
        col = "mazhou_density",
        style = "fisher",
        n = 5,
        palette = "Reds",
        title = "媽祖廟宇密度"
    ) +
    tm_shape(county) +
    tm_borders(col = "black")
tmap_arrange(map_count, map_level, map_density) #顯示三張並排地圖

