library(sf)
library(tmap)
library(ggplot2)
library(aspace)
library(dplyr)
library(RColorBrewer)

###建置環境
rm(list=ls())
setwd("C:/space analysis")
windowsFonts(TOP=windowsFont("AdobeGothicStd-Bold"))
windowsFonts(JF=windowsFont("微軟正黑體"))
TW=st_read("Popn_TWN2.shp",options="ENCODING=BIG5")
Dengue=st_read("Point_event.shp")
st_crs(TW) <- st_crs(Dengue)

##描述疾病擴散的時空趨勢
#By Week
cases <- Dengue %>% group_by(WEEK)%>%summarise(cases=n())
ggplot(cases) +
    geom_bar(aes(x = WEEK, y = cases), stat = "identity", fill = "skyblue") + 
    xlab("週次") +
    ylab("病例數") +
    scale_x_continuous(breaks = seq(0, 55, 5)) +
    theme_minimal() +
    theme(text = element_text(family = "TOP"))
#By Period
Dengue$Period <- ceiling((Dengue$WEEK+1)/8)
cases_by_period <- Dengue%>%group_by(Period)%>%summarise(cases=n())
ggplot(cases_by_period) +
    geom_bar(aes(x = Period, y = cases), stat = "identity") +
    xlab("區段") +
    ylab("病例數") +
    scale_x_continuous(breaks = 1:7) +
    theme_minimal() +
    theme(text = element_text(family = "TOP"))

#擷取高雄地區的登革熱病例分布
KH <- TW[TW$COUNTY=="高雄市",]
IN<- st_contains(st_union(KH),Dengue,sparse=F)
Dengue_KH <- Dengue[IN,]
Dengue_KH <- Dengue_KH%>%st_drop_geometry()

#Standard Distance
col=RColorBrewer::brewer.pal(7,"Reds")
map=tm_shape(KH,xlim=c(16,20)*10^4,ylim=c(249,252)*10^4)+tm_borders()
for(i in 1:7){
    Dengue_KHi <- Dengue_KH[Dengue_KH$Period==i,c("X","Y")]
    Dengue_KHi <- as.data.frame(Dengue_KHi)
    sdd_result <- calc_sdd(points=Dengue_KHi)
    center <- c(sdd_result$ATTRIBUTES$CENTRE.x,sdd_result$ATTRIBUTES$CENTRE.y)
    center_sf <- center%>%st_point%>%st_sfc%>%st_sf
    st_crs(center_sf) <- st_crs(KH)
    rad <- sdd_result$ATTRIBUTES$SDD.radius
    SDD <- st_buffer(center_sf,rad)
    map=map+tm_shape(center_sf)+tm_symbols(size = 0.5, col = col[i])+tm_shape(SDD)+tm_borders(col = col[i], lwd = 2)
}
print(map)

#Standard Deviational Ellipse
col=c("red","orange","yellow","green","blue","deepskyblue","purple")
map2=tm_shape(KH,xlim=c(16,20)*10^4,ylim=c(249,252)*10^4)+tm_borders()
for(i in 1:7){
    Dengue_KHi <- Dengue_KH[Dengue_KH$Period==i,c("X","Y")]
    Dengue_KHi <- as.data.frame(Dengue_KHi)
    sde_result <- calc_sde(points=Dengue_KHi)
    center <- c(sde_result$ATTRIBUTES$CENTRE.x,sde_result$ATTRIBUTES$CENTRE.y)
    center_sf <- center%>%st_point%>%st_sfc%>%st_sf
    st_crs(center_sf) <- st_crs(KH)
    # 獲取 SDE 的邊界點
    sde_data <-as.data.frame(cbind(sde_result$LOCATION$x,sde_result$LOCATION$y))
    colnames(sde_data) <- c("x","y")
    sde_pt_sf <-st_as_sf(sde_data,coords=c("x","y"))
    st_crs(sde_pt_sf) <- st_crs(KH)
    st_polygon_sf <- st_cast(st_combine(sde_pt_sf),"POLYGON")
    map2=map2+tm_shape(center_sf)+tm_symbols(size = 0.5, col = col[i])+tm_shape(st_polygon_sf)+tm_borders(col = col[i], lwd = 2)
}
print(map2)