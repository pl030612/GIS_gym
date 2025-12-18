
# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(tmap) #互動式及靜態地圖繪製
library(raster) #用於讀取網格資料

setwd("C:/Data/CH3")
hospital = st_read(dsn = "Taipei_hospital.shp")
village = st_read(dsn = "Taipei_village.shp")
flood.raster = raster("Taipei_flood200.tif")
windowsFonts(JH = windowsFont("微軟正黑體"))
tmap_mode('view') #tamp切換為互動式


# 3-1：評估淹水受災區（以幾何中心點疊圖分析） -----------------------------------------------------

##1.建立臺北市村里的幾何中心點
centroids <- st_centroid(village)

##2.捨去淹水不到0.5m的網格
flood.raster[values(flood.raster) < 0.5] <- NA

##3.將淹水潛勢資料格式轉換、進行合併及投影轉換
flood <- flood.raster %>%
    as("SpatialPolygonsDataFrame") %>% #網格轉向量sp格式
    st_as_sf() %>% #將sp格式轉為sf格式
    st_union() %>% #融合面資料
    st_transform(crs = st_crs(village)) #投影座標轉換成一致的座標

##4.篩選出被影響村里及繪圖
cen_id <- which(st_covered_by(centroids,flood,sparse=F))

##5.繪圖
plot(st_geometry(village)) #繪製所有村里底圖
plot(st_geometry(flood),#疊加淹水區
    col = "blue",
    border = NA,
    add = TRUE
) 
plot(st_geometry(centroids[cen_id,]), #疊加受影響的村里
     col = "red",
     pch = 20,
     add = TRUE) 

plot(st_geometry(village))#受影響的村里面量圖
plot(st_geometry(village[cen_id, ]), col = "red", add = TRUE)








# 3-2：評估淹水受災區（以行政區邊界疊圖分析） -------------------------------------------------------

##1.檢查哪些村里與淹水區接觸
vill_id <- which(st_is_within_distance(flood, village, dist = 0, sparse = FALSE))

##2.淹水區與受影響的村里
par(family = "JH", mar = c(1, 1, 1, 1)) #設定圖框與字型
plot(st_geometry(village)) #繪製所有村里底圖
plot(st_geometry(village[vill_id, ]), col = "red", add = TRUE) #疊加受影響的村里
plot(st_geometry(flood), #疊加淹水區
    col = "blue",
    border = NA,
    add = TRUE
)




# 3-3：評估受災影響人數 ----------------------------------------------------------

##1.村里中心點法
affected_by_centroids = sprintf("以村里中心點估計，有%d個村里受災，受災人數為%d人",
                                length(cen_id),
                                sum(village$Total[cen_id]))
print(affected_by_centroids)

##2.村里面空間法
affected_by_boundary = sprintf("以村里面空間估計，有%d個村里受災，受災人數為%d人",
                               length(vill_id),
                               sum(village$Total[vill_id]))
print(affected_by_boundary)

##3.淹水面積比例法
VF = st_intersection(village, flood)
village$flood_area = 0 #先將flood_area欄位都預填入0
village$flood_area[vill_id] = st_area(VF) #記錄每個村里的淹水面積
village$damaged_pop = #按淹水面積比例計算受災人數
    round(village$Total * village$flood_area / st_area(village)) 
affected_by_area = 
    sprintf("以村里淹水面積估計受災人數為%d人", sum(village$damaged_pop,na.rm = TRUE))
print(affected_by_area)










# 3-4：呈現受災影響的估計人口：脆弱人口密度分布圖 ---------------------------------------------------------

##1.計算脆弱人口和密度
A65_up.df = st_drop_geometry(village[, 25:32]) #取得高齡人口欄位
village$A65_up = rowSums(A65_up.df) #計算高齡人口總數
village$vulpop = 
    round(village$A65_up * village$flood_area / st_area(village)) #計算受災的高齡人口數
village$vden = 
    village$vulpop / st_area(village) * 10^6 #每平方公里脆弱人口密度

##2.脆弱人口密度分布圖
tm_shape(village) +
    tm_fill(
        col = "vden", 
        palette = "Reds", 
        style = "fisher", 
        n = 7, 
        title = "脆弱人口密度(人/平方公里)"
    ) +
    tm_borders() +
    tm_layout(
        title = "台北市200年重現期降雨淹水事件受災脆弱人口密度面量圖",
    ) +
    tm_scale_bar(position = c("left", "bottom")) #加上比例尺 





# 3-5：環域＋疊圖分析 -----------------------------------------------------------

##1.建立醫院1公里環域範圍
hospital_1km = st_buffer(hospital,dist=1000)
##2.找出和醫院1公里沒有交集的村里
vill.host_id = which(lengths(st_is_within_distance(village,hospital_1km,dist=0))==0) 
print(length(vill.host_id))
##3.疊圖分析
par(mar=c(1,1,1,1))
plot(st_geometry(village)) #繪製所有村里底圖
plot(st_geometry(village[vill.host_id,]),col='orange',add=T) #疊加和醫院1公里沒有交集的村里
plot(st_geometry(
    hospital_1km), #疊加醫院1公里環域範圍
    col="#FF004455",
    pch=20,
    border=NA,
    cex=2,
    add=T) 
plot(st_geometry(hospital),col='red',pch=20,cex=1,add=T) #疊加醫院




# 3-6：鄰近性分析 -------------------------------------------------------------

##1.計算各里中心到馬偕醫院的距離
MMH = subset(hospital,attr_ANNO=="馬偕醫院") #篩選出馬偕醫院
cen_MMH = st_distance(MMH,centroids)#計算各里中心到醫院的距離

##2.挑選離馬偕醫院最近的五個里
near5_MMH = order(cen_MMH)[1:5]#依距離排序後出最近的五個里
sprintf("馬偕醫院最近的五個里的人口數總和為%d人",sum(village$Total[near5_MMH]))

