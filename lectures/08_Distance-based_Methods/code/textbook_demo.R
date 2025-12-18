# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(spatstat) #點模式分析G函數、F函數、Ripley’s K函數、L函數
library(shotGroups) #分析點模式數據

setwd("C:/Data/Ch5")
school=st_read(dsn="Tainan_schools.shp")
town=st_read(dsn="Tainan_county.shp")
grid=st_read(dsn="grid5X5.shp")

##點轉換成ppp格式
school.ppp = as.ppp(school)

#F函數：Fest
F.CI = envelope(school.ppp, Fest)
plot(F.CI)

##K函數：Kest
K.CI = envelope(school.ppp, Kest)
plot(K.CI)

##L函數：Lest
L.CI=envelope(school.ppp, Lest)
plot(L.CI) 

