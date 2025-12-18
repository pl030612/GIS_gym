###初步環境建置與讀取檔案
library(sf)
library(tmap)
library(pals)
library(cartography)
library(grid)
library(ggplot2)

setwd("C:/space analysis")
EPA=st_read("EPA_STN2.shp",options="ENCODING=BIG5")
TW=st_read("Popn_TWN2.shp",options="ENCODING=BIG5")
windowsFonts(TOP=windowsFont("Topedia Sans TW Beta"))
windowsFonts(JF=windowsFont("jf金萱 半糖"))

###前導:人口數與空汙
##tmap
    #總人口數:各年齡層相加
TW$POP=TW$A0A14_CNT+TW$A15A64_CNT+TW$A65UP_CNT
plot(TW["POP"])
    #總人口數:分段
plot(TW["POP"],breaks="jenks",nbreaks=6,pal=brewer.blues(6))
    #總人口數:分段
brk=getBreaks(v=TW$POP,nclass=6,method="jenks")
tm_shape(TW)+tm_polygons("POP",title="人數",palette="-GnBu",breaks=brk)
    #比較
tm_shape(TW)+tm_polygons("POP")
    #點圖
tm_shape(TW)+tm_dots(size = .5)
    #人口密度+空氣偵測
tm_shape(TW)+tm_polygons("POP")+
    tm_shape(EPA)+tm_dots(col="red",size=.2)+tm_layout(frame=F)# 隱藏地圖邊框
    #並排
tmap1=tm_shape(TW)+tm_polygons("POP")
tmap2=tm_shape(EPA)+tm_dots(size=.2)
tmap_arrange(tmap1,tmap2,ncol=2,nrow=1)
    #2x2
grid.newpage()
pushViewport(viewport(layout=grid.layout(2,2)))
print(tmap1,vp=viewport(layout.pos.col=1,layout.pos.row=1))
print(tmap2,vp=viewport(layout.pos.col=2,layout.pos.row=2))

##qtm
qtm(TW,fill="POP")
qtm(TW,fill="POP",fill.title="人口",title="地圖",fill.palette="-Blues")
    #人口密度+空氣偵測_qtm
qtm(TW)+qtm(EPA,symbols.size=1,symbols.col = "red")
    #人口密度+空氣偵測_qtm+tmap
qtm(TW,fill="POP",fill.palette="-Blues")+
    tm_shape(EPA)+tm_dots(col="red",size=.2)+tm_layout(frame=F)

###實習一
#建立繪製地圖的函數 Pollution_Map(arg1)；引數arg1是可自行設定的超越機率(e.g. 0.2)
#1. 該函數會回傳該超越機率所對應的PSI值。
Pollution_Map = function(arg1) {
    # 回傳超越機率對應的PSI
    ind = qnorm(arg1, 59, 17.4, F)
    
    # 繪製空氣汙染圖
    highEPA = EPA[EPA$PSI > ind, ]
    lowEPA = EPA[!EPA$PSI > ind, ]
    
    # 繪製地圖
    map = tm_shape(TW, xlim = c(146500, 351000), ylim = c(240000, 2850000)) +
        tm_polygons(col = "green4", border.col = "grey20", lwd = 0.1) +
        tm_scale_bar(width = 0.3) +
        tm_compass(position = c(.05, .8)) +
        tm_layout(frame = F, title = "台灣空氣汙染圖", title.size = 1, title.position = c("center", "top"), fontfamily = "JF", asp = 0) +
        tm_shape(highEPA) + tm_dots(col = "red", size = 0.2) +
        tm_shape(lowEPA) + tm_dots(col = "blue", size = 0.2) +
        tm_add_legend("symbol", labels = c("高於臨界值", "低於臨界值"), col = c("red", "blue"))
    
    # boxplot呈現PSI
    highEPA = highEPA[highEPA$SiteType %in% c("一般測站", "交通測站", "工業測站"), ]
    boxplot = ggplot(highEPA, aes(x = SiteType, y = PSI)) +
        geom_boxplot() +
        ggtitle("高於臨界值的PSI盒狀圖") +
        xlab("測站類別") + theme_minimal() +
        theme(plot.margin = unit(c(1, 1, 1, 1), "cm"), plot.title = element_text(hjust = 0.5), text = element_text(family = "JF"))
    
    # 繪圖排列
    grid.newpage()
    pushViewport(viewport(layout = grid.layout(1, 2)))
    print(map, vp = viewport(layout.pos.col = 1))
    print(boxplot, vp = viewport(layout.pos.col = 2))
    
    return(ind)
}

Pollution_Map(0.3)

###作業
##台灣人口密度
    #總人口數:各年齡層相加
library(units)
TW$POP=TW$A0A14_CNT+TW$A15A64_CNT+TW$A65UP_CNT
    #設定單位
TW$AREA=set_units(st_area(TW),"km^2")
TW$Density=TW$POP/as.numeric(TW$AREA)
brk = getBreaks(v = TW$Density, nclass = 6, method = "quantile")
tm_shape(TW) +
    tm_polygons("Density", title = "Population Density", palette = "-GnBu", breaks = brk) +
    tm_layout(outer.margins = c(0.05, 0.05, 0.05, 0.05))
##大台北人口老化地圖
Taipei <- TW[TW$COUNTY=="臺北市",]
brk=getBreaks(v=Taipei$A65UP_CNT,nclass=4,method="quantile")
tm_shape(Taipei)+
    tm_polygons("A65UP_CNT",title="Population of 65 up", palette = "-GnBu", breaks = brk)+
    tm_layout(outer.margins = c(0.05,0.05,0.05,0.05))
##Boxplot:比較各地區的老年人口分布及不同年齡結構的人口分布
boxplot1=ggplot(TW,aes(x=TW$COUNTY,y=TW$A65UP_CNT))+
    geom_boxplot()+
    ggtitle("各地區65歲以上人口分布")+
    xlab("縣市")+
    ylab("人口數")+
    theme(plot.margin = unit(c(1, 1, 1, 1), "cm"), plot.title = element_text(hjust = 0.5), text = element_text(family = "JF"))
boxplot2=ggplot(TW,aes(x=TW$COUNTY,y=TW$A15A64_CNT))+
    geom_boxplot()+
    ggtitle("各地區15-64歲人口分布")+
    xlab("縣市")+
    ylab("人口數")+
    theme(plot.margin = unit(c(1, 1, 1, 1), "cm"), plot.title = element_text(hjust = 0.5), text = element_text(family = "JF"))
boxplot3=ggplot(TW,aes(x=TW$COUNTY,y=TW$A0A14_CNT))+
    geom_boxplot()+
    ggtitle("各地區14歲以上人口分布")+
    xlab("縣市")+
    ylab("人口數")+
    theme(plot.margin = unit(c(1, 1, 1, 1), "cm"), plot.title = element_text(hjust = 0.5), text = element_text(family = "JF"))
# 繪圖排列
grid.newpage()
pushViewport(viewport(layout = grid.layout(3, 1)))
print(boxplot1, vp = viewport(layout.pos.row = 1))
print(boxplot2, vp = viewport(layout.pos.row = 2))
print(boxplot3, vp = viewport(layout.pos.row = 3))