
# 環境設定與載入資料 ---------------------------------------------------------------

library(sf) #處理及讀取空間資料
library(spdep) #空間權重矩陣及空間自相關分析
library(RColorBrewer) #建立色階
library(units) #單位轉換和處理的工具

setwd("C:/Data/CH8")
dengue=st_read(dsn="Dengue_Case.shp")
town=st_read(dsn="KAOH_town.shp")


# 8-1：計算Gi*進行熱區分析 -----------------------------------------------------

##1.設計所需的函數
#1.1FDR校正(輸入校正前的Gi*，將輸出FDR校正後的Gi*)
FDR.adjust=function(Gi){ 
    Gi=as.numeric(Gi) #確保數值類型
    p=mapply(function(x) pnorm(x,lower.tail=x<0),Gi) #轉換為p值
    p.fdr=p.adjust(p,"fdr") #轉換為fdr校正後p值
    Gi.fdr=qnorm(p.fdr)*-sign(Gi) #轉換為有正負號的Z分數
    return(Gi.fdr)
}

#1.2熱區分析函數(放入多邊形、數值、鄰近距離閾值三個參數得到冷熱區顏色)
col7=rev(brewer.pal(7,"RdBu")) #建立紅藍色7階並反轉顏色順序
OptimizedHotSpot=function(poly,num,dist){ 
    coord=st_coordinates(st_centroid(poly)) #計算中心點座標
    dnear=dnearneigh(coord, d1=0, d2=dist) #建立鄰近關係
    dnear=include.self(dnear) #Gi*鄰近定義須包含自己
    dw=nb2listw(dnear,zero.policy=T,style="W") #轉換為listw
    Gi=localG(num,dw) #計算Gi指數*
    Gi.fdr=FDR.adjust(Gi) #用前述設計的FDR校正函數校正
    poly$Gi=cut(Gi.fdr,qnorm(c(0,.005,.025,.05,.95,.975,.995,1))) #將Gi轉換為7個等級
    poly$Gi_col=col7[poly$Gi] #對應上7個色階
    return(poly$Gi_col)
}

##2.尺度為六邊形網格
hex=st_make_grid(dengue,600,square=F) #建立邊長600公尺六邊形網格
hex=st_sf(hex)
hex$COUNT=lengths(st_contains(hex,dengue)) #計算網格內病例數
hex=hex[hex$COUNT!=0,] #過濾掉病例數0的網格
hex$col=OptimizedHotSpot(hex,hex$COUNT,6211) #冷熱區著色

##3.尺度為行政區
town$COUNT=lengths(st_contains(town,dengue)) #計算行政區內病例數
town$col=OptimizedHotSpot(town,town$COUNT,15138) #冷熱區著色

##4.繪圖
par(mar=c(0,0,0,0))
par(mfrow=c(1,2))
plot(st_geometry(hex),col=hex$col) #尺度為六邊形的冷熱區結果
plot(st_geometry(town),border.col='#DDDDDD',add=T) #行政區邊框
plot(st_geometry(town),col=town$col) #尺度為行政區的冷熱區結果



# 8-2：進行人口校正的熱區分析 -------------------------------------------------------

##1.計算各行政區的感染人數比例
town$CASE_PRCNT=town$COUNT/town$CENSUS*1000

##2.計算Gi*分析感染病例冷熱區及繪圖
town$col_PRCNT=OptimizedHotSpot(town,town$CASE_PRCNT,15138)
plot(st_geometry(town),col=town$col_PRCNT)



# 8-3：最佳化參數設定與統計顯著性校正 ----------------------------------------------------------

##1.熱區分析
center=st_centroid(town)
coord=st_coordinates(center)
dnear=dnearneigh(coord, d1=0, d2=14012) #以行政區中心點之間距離來計算鄰近關係
dnear=include.self(dnear) #Gi*鄰近定義須包含自己
town.dw=nb2listw(dnear,zero.policy=T,style="W") #列標準化
town$Gi=localG(town$CASE_PRCNT,town.dw) #計算Gi指數*
town$Gi.fdr=FDR.adjust(town$Gi) #以FDR函數進行校正
town$Gi_col=col7[cut(town$Gi,
                     qnorm(c(0,.005,.025,.05,.95,.975,.995,1)))] #無FDR校正所對應的顏色
town$Gi.fdr_col=col7[cut(town$Gi.fdr,
                         qnorm(c(0,.005,.025,.05,.95,.975,.995,1)))] #有FDR校正所對應的顏色

##2.繪圖
par(mar=c(0,0,0,0))
par(mfrow=c(1,2))
plot(st_geometry(town),col=town$Gi.fdr_col)
plot(st_geometry(town),col=town$Gi_col)



# 8-4：計算Local Moran’s找出熱區與冷區 ---------------------------------------------------------

##1.產生鄰近關係矩陣
dist=st_distance(center)
dist=drop_units(dist)
weight=1/dist
weight[dist>14012]=0
diag(weight)=0
town.nbw=mat2listw(weight)

##2.計算LISA值(Local Moran's I)
LISA=localmoran_perm(town$CASE_PRCNT,town.nbw,alternative='two.sided')
LISA=as.data.frame(LISA) #轉換為data.frame以便後續分析

##3.分類空間關聯類型(H-H/L-L/H-L/L-H/不顯著五組)
col=c() #建立空列表
colors=c("red", "blue", "lightpink", "skyblue2", "#F2F2F2")#設定五種顏色
LISA$diff=town$CASE_PRCNT-mean(town$CASE_PRCNT) #判斷該區病例比例高於還是低於平均值
col[LISA$Z.Ii>0 & LISA$diff>0]=colors[1] #H-H，該區與鄰近區域皆為高病比例(紅色)
col[LISA$Z.Ii>0 & LISA$diff<0]=colors[2] #L-L，該區與鄰近區域皆為低病比例(藍色)
col[LISA$Z.Ii<0 & LISA$diff>0]=colors[3] #H-L，該區病例比例高但周圍為低(粉紅色)
col[LISA$Z.Ii<0 & LISA$diff<0]=colors[4] #L-H，該區病例比例低但周圍為高(淺藍色)
col[LISA$`Pr(z != 0)`>0.1]=colors[5] #Not_Significant，無顯著空間聚集模式

##4.繪圖
par(mar=c(0,0,0,0)) 
plot(st_geometry(town), col = col)
legend( 
    "bottomright",#調整圖例外觀
    legend = c("High-High","Low-Low","High-Low","Low-High","Not Significant"),
    fill = colors,
    bty = "n", #不顯示圖例的邊框
    cex = 0.7, #字體縮小到70%
    y.intersp = 1, #圖例每行的垂直間距
    x.intersp = 1) #圖例符號與文字的水平間距




