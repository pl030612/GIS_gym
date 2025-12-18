library(sf)
library(tmap)
library(dplyr)
library(units)

###建置環境
rm(list=ls())
setwd("C:/space analysis")
TPE=st_read("Taipei_Vill.shp",options="ENDCOING=BIG5")
FF=st_read("Tpe_Fastfood.shp",options="ENDCOING=BIG5")
st_crs(TPE)
st_crs(FF)
MC=FF[FF$STORE=="MIC",]

###以台北市為範圍，麥當勞 1 km為服務範圍內所涵蓋的麥當勞分店數，定義為該家麥當勞店家的連鎖密度，請問哪一家麥當勞的連鎖密度最高？ 繪製在地圖上，並標示該店家名稱。
##連鎖密度最高的麥當勞
TPE_bg <- tm_shape(TPE)+tm_polygons("grey90")
MC_pts <- tm_shape(MC)+tm_dots(col="#FB6A4A",size = 0.5)


#buffer
MC_buffer_sf <- st_buffer(MC,dist=1000)
MC_buffer <- tm_shape(MC_buffer_sf)+tm_polygons("yellow",alpha = 0.2)
TPE_bg+MC_pts+MC_buffer

#identifying service area
distance_matrix <- st_distance(MC,MC)
distance_matrix <- set_units(distance_matrix,km)
less_1km <-apply(distance_matrix<set_units(1, km),1,sum)-1 #減去自身# 確保1公里也是 "units" 物件

max_chain_density <- which.max(less_1km)

map <-TPE_bg+
    MC_pts+
    tm_shape(MC[max_chain_density,])+
    tm_dots(col = "blue",size=0.7)+
    tm_text("ALIAS",size=1,col="black",xmod=0.5)+
    tm_layout(outer.margins = c(0.05,0.05,0.05,0.05))
print(map)
    

##以台北市為範圍，麥當勞 1 km為服務範圍。以台北市各里中心點是否在涵蓋該麥當勞的服務範圍，作為判斷該麥當勞是否能服務到該里的標準。請問哪個里可被麥當勞服務的家數最多？繪製在地圖上，並標示該里的位置及可及的麥當勞店家。
#各里中心點到麥當勞的距離
TPE_center_sf <- st_centroid(TPE)
distance_matrix_mc_vill <- st_distance(TPE_center_sf,MC)
distance_matrix_mc_vill <-set_units(distance_matrix_mc_vill,km)
#計算各里中心到麥當勞距離小於1km的數量
less_1km_mc_vill <- apply(distance_matrix_mc_vill<set_units(1,km), 1, sum)
max_vill <- which.max(less_1km_mc_vill)
#找到可被最多麥當勞服務的里
max_vill_name <- TPE$VILLAGE[max_vill]
print(max_vill_name)
max_vill_sf <- TPE[max_vill,]
#找到該里可及的麥當勞店家
reachable_mc <- which(distance_matrix_mc_vill[max_vill,]<set_units(1,km))
print(MC$ALIAS[reachable_mc])
reachable_mc_sf <- MC[reachable_mc,]
#繪製地圖
map2 <- TPE_bg+
    tm_shape(max_vill_sf)+
    tm_dots(col="blue",size=0.7)+
    tm_shape(reachable_mc_sf)+
    tm_dots(col="yellow",size=0.3)
print(map2)

