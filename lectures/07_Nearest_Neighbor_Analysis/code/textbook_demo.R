# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(spatstat) #點模式分析G函數、F函數、Ripley’s K函數、L函數
library(shotGroups) #分析點模式數據

setwd("C:/Data/Ch5")
school=st_read(dsn="Tainan_schools.shp")
town=st_read(dsn="Tainan_county.shp")
grid=st_read(dsn="grid5X5.shp")

# 5-2：最鄰近分析 -------------------------------------------------------

##1.點轉換成ppp格式
school.ppp = as.ppp(school)

##2.計算研究區面積，以最小包圍矩形為範圍
MBR = getMinBBox(st_coordinates(school))
school.area = MBR$width * MBR$height

##3.計算k階鄰近點之距離，預設k=1
r_obs = mean(nndist(school.ppp)) #計算樣本的最近鄰距離平均數
r_exp = sqrt(school.area / nrow(school)) / 2 #計算隨機分布的最近鄰距離期望值 
se = 0.26136 * sqrt(school.area) / nrow(school) #計算標準誤 
R = r_obs / r_exp #計算檢定值
z = (r_obs - r_exp) / se #計算標準化z值
sprintf("R值為%.4f，z值為%.4f。", R, z)  #結論判定








# 5-3：距離函數的分析方法－G函數及F函數 ----------------------------------------------------------

#G函數：Gest
G.CI = envelope(school.ppp, Gest)
plot(G.CI)