


# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(spdep) #空間權重矩陣及空間自相關分析
library(units) #單位轉換和處理的工具

setwd("C:/DATA/Ch7")
dengue = st_read(dsn = "Dengue_Case.shp")
town = st_read(dsn = "KAOH_town.shp")


# 7-1：Moran’s I-----------------------------------------------------

##1.計算各行政區的感染人數比例
town$COUNT = lengths(st_contains(town, dengue)) #各行政區的病例數
town$CASE_PRCNT = town$COUNT / town$CENSUS * 1000 #每千人中的感染比例

##2.建立行政區的鄰近關係矩陣
center = st_centroid(town) #行政區中心點
dist = st_distance(center) #計算距離矩陣
dist = drop_units(dist) #轉換成數值矩陣


##3.鄰近關係矩陣轉換成listw並進行列標準化
weight = 1 / dist #距離的倒數作為權重
weight[dist > 14012] = 0 #閾值設為14012公尺
diag(weight) = 0 #自身非鄰近關係(對角線填入0)
town.nbw = mat2listw(weight, style = "W") #轉換為listw鄰近格式

##4.計算Moran's I指數
moran.test(town$CASE_PRCNT, town.nbw)






# 7-2：Incremental Moran’s I -------------------------------------------------------

##1.設定距離範圍
coord = st_coordinates(center)
dists = seq(14011, 24156, length.out = 10) #設定鄰近距離閾值
DATAs = c() #空的變數用來存放後續的Moran’s I結果

##2.以迴圈的方式計算各個距離的Moran's I
for (d in dists) {
    dnear = dnearneigh(coord, d1 = 0, d2 = d) #設定d1~d2距離內為鄰近的定義
    town.dw = nb2listw(dnear, zero.policy = T, style = "W") #zero.policy=T允許沒有鄰居的觀測點
    moran = moran.test(town$CASE_PRCNT, town.dw, alternative = "two.sided") #以雙尾計算p-value
    data = as.numeric(c(moran$estimate, moran$statistic, moran$p.value)) #儲存結果
    DATAs = rbind(DATAs, data) #每一次迴圈結果黏回現存DATAs
}

DATAs = data.frame(DATAs) #DATAs轉換為 data.frame
colnames(DATAs) = c("Moran's I", "Expectation", "Variance", "Z.score", "p.value") #欄名稱
rownames(DATAs) = round(dists, 2) #列名稱為標示對應的距離閾值，取至小數第二位

##3.繪製 Z-score 與距離的關係圖
plot(DATAs$Z.score ~ dists,
     type = 'b',
     #同時繪製點與線
     xlab = "Distance",
     ylab = "z-score")



# 7-3：G-statistics ----------------------------------------------------------

##1.計算G指數
globalG.test(town$CASE_PRCNT, town.nbw)
