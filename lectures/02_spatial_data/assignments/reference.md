## 作業：繪製人口老化地圖與統計圖表

```{r message=FALSE, warning=FALSE}
rm(list=ls())
library(sf)
library(tmap)
library(pals)
library(cartography)
library(dplyr)
library(ggplot2)

setwd("C:/Users/User/Downloads/20260228")
TW=st_read("Popn_TWN2.shp", options="ENCODING=BIG5", quiet=T)
```

```{r message=FALSE, warning=FALSE}
class(TW)
head(TW)
```

## 1: 台灣人口密度地圖

```{r message=FALSE, warning=FALSE}
TW$area_m2 = st_area(TW)
TW$area_km2 = as.numeric(TW$area_m2) / 1e6
```
```{r message=FALSE, warning=FALSE}
TW$popn = TW$A0A14_CNT + TW$A15A64_CNT + TW$A65UP_CNT
TW$density = TW$popn / TW$area_km2
```
```{r message=FALSE, warning=FALSE}
plot(TW["density"], breaks = "quantile", nbreaks = 6, pal=brewer.blues(6))

breakv = getBreaks(v = TW$density, nclass = 6, method = "quantile")

tm_shape(TW) +
  tm_polygons("density", title = "population density", palette = "blue", 
              breaks = c(breakv)) +
  tm_scalebar() +
  tm_compass(position = c(0.8, 0.3)) +
  tm_layout(frame = T, title = "Taiwan population density map", 
            title.size = 1, title.position = c("top", "right"))
```

## 2: 大台北人口老化地圖

```{r message=FALSE, warning=FALSE}
TW$aging_population = TW$A65UP_CNT / TW$popn * 100
```
```{r message=FALSE, warning=FALSE}
func1=function(a){
  qnorm(a, mean = 14.75979, sd = 3.893547, lower.tail = FALSE, log.p = FALSE)
}
n=func1(a=0.2)
n
```
```{r message=FALSE, warning=FALSE}
taipei_area = dplyr::filter(TW, COUNTY %in% c("臺北市", "新北市", "桃園市", "基隆市", "宜蘭縣"))
highaging=taipei_area[taipei_area$aging_population>=n,]
map = tm_shape(taipei_area,xlim=c(206500,385000),ylim=c(2650000,2850000)) +
   tm_polygons(col='grey',border.col='grey20',lwd=0.1) +
   tm_scalebar() +
   tm_compass(position = c(0.05,0.8)) +
   tm_layout(frame = T, title = "Taipei aging population degree",title.size = 1, title.position = c("top", "left"))
map = map + tm_shape(highaging) + tm_polygons(col="red",border.col='grey20',lwd=0.1)
map = map + tm_add_legend(title = "鄉鎮人口", labels=c("老年人口比例佔全區前20%","其他"),fill=c("red","grey"))
map
```

## 3: Boxplot: 比較各地區的老年人口分布以及不同年齡結構的人口分布

### [3-1]比較台灣的高人口密度vs. 低人口密度的老年人口比例的分布

```{r message=FALSE, warning=FALSE}
highdensity = dplyr::filter(TW, density > 10000)
lowdensity=dplyr::filter(TW, density <2000)
boxplot(highdensity$aging_population, lowdensity$aging_population, names=c("高密度", "低密度"), ylab="65歲以上人口比例", main="不同人口密度之老年人口比例分布")
```

### [3-2]比較台灣老/中/青年群族的鄉鎮人口數分布

```{r message=FALSE, warning=FALSE}
population_2=subset(TW, select=c("A0A14_CNT", "A15A64_CNT", "A65UP_CNT"))
population_2_long=reshape(population_2,
                          varying = c("A0A14_CNT", "A15A64_CNT", "A65UP_CNT"),
                          v.names = "population",
                          timevar = "age_group",
                          times = c("青年", "中年", "老年"),
                          direction = "long")
population_2_long$age_group <- factor(population_2_long$age_group, levels = c("青年", "中年", "老年"))
plot2=ggplot(population_2_long, aes(x=age_group, y=population))+geom_boxplot()+ggtitle("台灣老/中/青年群族的鄉鎮人口數分布")
plot2
```