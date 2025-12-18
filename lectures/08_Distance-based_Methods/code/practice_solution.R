install.packages("splancs")
library(splancs)
library(sf)
library(spatstat)
library(rgdal)
library(GISTools)

setwd("C:/space analysis")
school <- st_read("Schools.shp")
Tainan <- st_read("TainanCounty.shp")
school_coord <- st_coordinates(school)

###計算台南市學校的分布狀況
#轉成ppp格式
TN <- as.owin(Tainan)
SH <- as.ppp(school,TN)
n <- SH$n

#產生隨機點，計算最鄰近距離
CRS <- rpoint(100,win=TN)
NND <- nncross(X=CRS,Y=SH)

#計算F(d)和ecdf()
Fd <- ecdf(NND$dist)

##蒙地卡羅
#建立一個99(模擬次數)*100(隨機點數量)的矩陣，儲存每次計算的最鄰近距離
F_sim <- matrix(nrow=99,ncol=100)
#使用迴圈生成隨機點存入矩陣
for(i in 1:99) F_sim[i,]=nncross(CRS,rpoint(n,win=TN))$dist
F_sim_sort <- apply(t(apply(F_sim,1,sort)),2,sort)

##繪圖
#p 繪製 Fd 的圖形
plot(Fd, col = "red", cex = 0, main = "F function", xlab = "distance", ylab = "F(d)", xlim = c(0, 4000))

#在圖上繪製每一列 F_sim 的 ECDF
for (i in 1:99) {
    lines(ecdf(F_sim[i,]), col = "grey", verticals = TRUE, cex = 0)
}
lines(ecdf(F_sim_sort[5,]),verticals=T,col="blue",cex=0,lwd=1.5)
lines(ecdf(F_sim_sort[95,]),verticals=T,col="blue",cex=0,lwd=1.5)
lines(Fd,col="red",verticals=T,cex=0,lwd=3)

##用包絡曲線函數去繪製
CI <- envelope(SH,Fest,nsim = 99,nrank=5)
plot(CI)

###台北市KFC是否顯著群聚在MIC附近
##H0:兩者隨機 Ha:兩者群聚，KFC在MIC附近
FF <- st_read("Tpe_Fastfood.shp")
#轉換為 sp 格式
FF_sp <- as(FF, "Spatial")
isS4(FF_sp)
##spatstat-Kcross
FF_ppp <- ppp(FF_sp@coords[,1],FF_sp@coords[,2],FF_sp@bbox[1,],FF_sp@bbox[2,])
FF$STORE <- factor(FF$STORE)
FF_ppp <- FF_ppp %mark%FF$STORE
K <- Kcross(FF_ppp,"KFC","MIC",correction = "none")
K_env <- envelope(FF_ppp,Kcross,verbose=F,nsim=99,nrank=5,alternative = "greater")
plot(K_env,main="Kcross+envelope(default)")

##splance-K12hat
s <- seq(0,3000,100)
FF_pts <- as.points(FF_sp@coords[,1],FF_sp@coords[,2])
KFC <-FF_pts[FF$STORE=="KFC"]
MIC <- FF_pts[FF$STORE=="MIC"]
KFC <- matrix(KFC, ncol = 2, byrow = TRUE)
MIC <- matrix(MIC, ncol = 2, byrow = TRUE)
KFC <- as.points(KFC[, 1], KFC[, 2])
MIC <- as.points(MIC[, 1], MIC[, 2])
x1 <- FF_sp@bbox[1,1]
x2 <- FF_sp@bbox[1,2]#x1和x2：X 軸的最小值與最大值
y1 <- FF_sp@bbox[2,1]
y2 <- FF_sp@bbox[2,2]#y1和y2：Y 軸的最小值與最大值
BND <- as.points(c(x1,x2,x2,x1,x1),c(y1,y1,y2,y2,y1))#從左下角(x1)開始，依序走到右下角(x2)、右上角、左上角，最後回到起點形成閉合矩形
tpe.k12 <- k12hat(KFC,MIC,BND,s)
env12 <- Kenv.tor(KFC,MIC,BND,19,s,quiet = T) #抑制模擬的進度顯示

plot(s,tpe.k12,type="l",xlab="dist",ylab="K(d)",main="k12hat+Kenv.tor")
polygon(c(s, rev(s)), c(env12$upper, rep(0, length(s))), col="grey")
line(s, tpe.k12, col="blue", lwd=2)