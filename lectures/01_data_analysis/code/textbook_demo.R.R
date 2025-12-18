
# 1-2安裝與載入套件 --------------------------------------------------------------

##1.安裝
install.packages("sf")
##2.載入套件
library(sf) #處理及讀取空間資料

# 1-3讀取GIS空間向量資料 ----------------------------------------------------------

##1.設定工作資料夾
getwd() #檢視目前工作資料夾
setwd("C:/Data/CH1") #將工作資料夾設定成 "C:/Data/CH1"
##2.清除環境變數
rm(list=ls())
##3.讀取shapefile資料
town=st_read(dsn = "Taiwan_town.shp") #相對路徑
town=st_read(dsn = "C:/Data/CH1/Taiwan_town.shp") #絕對路徑
town=st_read(dsn = "Taiwan_town.shp", options="ENCODING=BIG5") #更改中文編碼

library(installr)
updateR()
update.packages(ask = FALSE, checkBuilt = TRUE)