
# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(spatstat) #點模式分析G函數、F函數、Ripley’s K函數、L函數
library(shotGroups) #分析點模式數據

setwd("C:/Data/Ch5")
school=st_read(dsn="Tainan_schools.shp")
town=st_read(dsn="Tainan_county.shp")
grid=st_read(dsn="grid5X5.shp")


# 5-1：樣方分析 -----------------------------------------------------
##1.計算均勻網格內的學校總數
num = lengths(st_contains(grid, school))

##2.VMR檢定──t統計量單尾檢定
S.vmr = var(num) / mean(num) #VMR統計量
S.se = sqrt(2 / (nrow(grid) - 1)) #VMR標準誤
S.t = (S.vmr - 1) / S.se #t值
sprintf(
    "VMR統計量為%.4f，t值為%.4f。當顯著水準為0.05，右尾檢定的臨界值為%.3f，因此%s",
    S.vmr, #VMR統計量
    S.t, #t值
    qt(0.95, (nrow(grid) - 1)), #自由度df=n-1的95%臨界值
    ifelse(S.t > qt(0.95, (nrow(grid) - 1)),  #結論判定
           "落入拒絕域，表空間上有顯著群聚特徵。",
           "未落入拒絕域，無法拒絕虛無假設，空間分佈可能是隨機的。")
)



