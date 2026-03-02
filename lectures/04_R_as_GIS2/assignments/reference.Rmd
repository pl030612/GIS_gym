---
title: "作業單元 4 參考解答"
output:
  html_document:
    toc: true
    toc_depth: '3'
    df_print: paged
  html_notebook:
    toc: true
    toc_depth: 3
    toc_float:
      collapsed: false
      smooth_scroll: true
---

## 計算環域涵蓋人數的自訂函數

建立自訂函數，回傳使用者設定某捷運站在特定距離方圓內涵蓋的人數。   建立自訂函數STN_POP(id,dist)，其中id代表捷運站的編號，dist代表離捷運站的距離。該函數能回傳「編號id車站」在方圓距離「dist公尺」內涵蓋的人數（回傳整數格式），以涵蓋村里的面積加權計算人口數。 例如：STN_POP (38,500) 表示該函數回傳編號38的捷運站在500公尺方圓內所涵蓋的人口數。  

### 1. 讀檔案

```{r message=FALSE, warning=FALSE}
rm(list=ls())
library(tmap)
library(sf)
library(dplyr)
library(units)

MRT_sf=st_read("C:/Users/User/Downloads/20260228/MRT.shp",options="ENCODING=BIG5", quiet=TRUE)

TPE_LI_sf=st_read("C:/Users/User/Downloads/20260228/TPE_LI.shp",options="ENCODING=BIG5", quiet=TRUE)

```


```{r message=FALSE, warning=FALSE}

TPE_LI_sf=st_transform(TPE_LI_sf,3826)
st_crs(TPE_LI_sf)

st_crs(MRT_sf)

```
  
捷運站共有72站。   st_transform轉換坐標系統為一致。  

```{r message=FALSE, warning=FALSE}
MRT_lyr=tm_shape(MRT_sf)+tm_dots("red",size=0.3)
MRT_lyr
```


```{r message=FALSE, warning=FALSE}
TPE_lyr=tm_shape(TPE_LI_sf)+tm_polygons(col="CENSUS",
                                        palette="BLUES",
                                        border.col="black",
                                        title="每里人口數")

TPE_lyr
TPE_lyr+MRT_lyr
```


```{r message=FALSE, warning=FALSE}
MRT_loc=st_intersection(MRT_sf,TPE_LI_sf)
MRT_loc_lyr=tm_shape(MRT_loc)+tm_polygons("CENSUS")
MRT_loc_lyr
```

### 練習buffer: 設緩衝區距離500

```{r message=FALSE, warning=FALSE}
buffer=st_buffer(MRT_loc,500)
buffer_loc=st_intersection(buffer,TPE_LI_sf)
buffer_loc$area=st_area(buffer_loc)#緩衝區與里的交集面積，不過好像用不到，後面用match

buffer_lyr=tm_shape(buffer_loc)+tm_polygons("grey90")
buffer_lyr
```

### 練習match

```{r message=FALSE, warning=FALSE}
match(buffer_loc$V_ID,TPE_LI_sf$V_ID) #返回向量 表示buffer_loc每一塊polygon 在TPE_LI_sf對應的位子索引
```

## 練習計算buffer內加權人口數  
### 1.計算交集總面積

```{r message=FALSE, warning=FALSE}
# buffer_loc$vill_area=st_area(TPE_LI_sf)[match(buffer_loc$V_ID,TPE_LI_sf$V_ID)] 
TPE_LI_sf$vill_area=st_area(TPE_LI_sf)
buffer_loc=st_intersection(buffer,TPE_LI_sf)

buffer_loc$area=st_area(buffer_loc)

```

### 2.計算加權人口

```{r message=FALSE, warning=FALSE}
buffer_loc$population=round((buffer_loc$area/buffer_loc$vill_area)*buffer_loc$CENSUS.1)
mrt_id=MRT_loc[MRT_loc$MRT_ID==38,]
# dist=set_units(dist,"m")
buffer2=st_buffer(mrt_id,500)
TPE_LI_sf$vill_area=st_area(TPE_LI_sf)
buffer_loc2=st_intersection(buffer2,TPE_LI_sf)
  
buffer_loc2$area=st_area(buffer_loc2)
  
  
  # return(head(buffer_loc2))
buffer_loc2$population=(buffer_loc2$area/buffer_loc2$vill_area)*buffer_loc2$CENSUS.1
  
  # return(buffer_loc2)
  
total_population=round(sum(buffer_loc2$population))
print(total_population)

```

### 3.最終函式

```{r message=FALSE, warning=FALSE}
STN_POP=function(id,dist){
  mrt_id=MRT_sf[MRT_sf$MRT_ID==id,]
  dist=set_units(dist,"m")
  buffer2=st_buffer(mrt_id,dist)
  TPE_LI_sf$vill_area=st_area(TPE_LI_sf)
  buffer_loc2=st_intersection(buffer2,TPE_LI_sf)
  
  buffer_loc2$area=st_area(buffer_loc2)
  
  
  # return(head(buffer_loc2))
  buffer_loc2$population=(buffer_loc2$area/buffer_loc2$vill_area)*buffer_loc2$CENSUS
  
  # return(buffer_loc2)
  
  total_population=round(sum(buffer_loc2$population))
  return(total_population)
  # return(buffer2)
}

STN_POP(38,500)

```
