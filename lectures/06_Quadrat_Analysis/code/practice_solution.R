library(sf)
library(spatstat)

school <- st_read("C:/space analysis/Schools.shp",options="ENCOING=UTF8")
Tainan <- st_read("C:/space analysis/TainanCounty.shp",options="ENCOING=UTF8")

school_coord <- st_coordinates(school)
TN <- as.owin(Tainan)
SH <- as.ppp(school_coord,TN)
n<- length(unique(school$SCHOOL_ID))

###NNA
#H0:台南市學校為隨機分布
#H1:台南市學校為非隨機分布

r_obs <- mean(nndist(SH))
r_sim <- sapply(1:999,function(x) mean(nndist(rpoint(n,win=TN))))
r_sim <- sort(r_sim)

hist(r_sim,x_lim=c(900,1500),xlab="",main="NNA")
abline(v=r_obs,col="red")
abline(v=r_sim[c(25,975)],col="blue")

##K-order NNI
NNI_obs <- colMeans(nndist(SH,k=1:50))
NNI_sim <- sapply(1:2,function(x) colMeans(nndist(rpoint(n,win=TN),k=1:3)))
NNI_sim <- apply(NNI_sim,1,sort)

plot(c(0,51),c(0,NNI_sim[999,50],type="n",main="K-NNI",xlab="K-order",ylab="NNI",xaxs="i",yaxs="i"))
polygon(c(1:50,50:1),c(NNI_sim[25,],rev(NNI_sim[975,])),col="#0000FF22",border =NA)
line(1:50,NNI_sim[975,],col="blue",lty=3)
line(1:50,NNI_sim[25,],col="blue",lty=3)
line(1:50,NNI_sim[500,],co="blue")
line(1:50,NNI_obs,col="red",lty=3)
line(1:50,NNI_obs,col="red",pch=20,cex=1)


##G function
G_obs <- ecdf(nndist(SH))
plot(G_obs,lwd=3,cex=0,col="red",main="G(d)",xlab="distance",ylab="G(d)",xlim=c(0,5000),xaxs="i",yaxs="i")
#G_sim <- sapply(1:99,function(x) lines(ecdf(nndist(rpoint(n,win=TN))),cex=0))
#生成回機樣本並計算隨機G(d)函數:這段程式碼創建一個 99 x n 的矩陣 G_sim，每一行存儲一次隨機點分佈（使用 rpoint(n, win=TN) 生成隨機樣本）的最近鄰距離。
G_sim <- matrix(nrow = 99,ncol=n)
for (i in 1:99) G_sim[i,]=nndist(rpoint(n,win=TN))
#繪製隨機G(d)函數
for (i in 1:99) line(ecdf(G_sim[i,],cex=0,col="grey80"))
#繪製觀察到的G(d)函數
lines(G_obs,lwd=3,cex=0,col="red")
#計算和繪製隨機G(d)函數的信賴區間
#將G_sim按行排序，轉置t
G_sim2 <- t(apply(G_sim,1,sort))
#按列排序，使每一列的元素都是從小到大排列的距離值
G_sim3 <- apply(G_sim2,2,sort)
#繪製5%和95%的線
lines(ecdf(G_sim3[5,]),col="blue",cex=0)
lines(ecdf(G_sim3[95,]),col="blue",cex=0)