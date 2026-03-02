## Question 1

將實習所定義麥當勞的連鎖密度，建立chainstore(d)的自訂函數，可繪製服務半徑(d) vs.麥當勞的關係圖表。

### 連鎖密度（chain density）

麥當勞d km為服務範圍內所涵蓋的麥當勞分店數，定義為該家麥當勞店家的連鎖密度。

## Setting up
The `fastfood_all` variable is from `FASTFOOD.shp`, it is a data containing location imformations of fastfood shops in Taipei; and the variable `tpe_county` is from `Taipei_Vill.shp`.
```{r message=FALSE, warning=FALSE}
rm(list = ls())
library(sf)
library(tmap)
library(units)

fastfood_all = st_read("C:/Users/User/Downloads/20260228/Tpe_Fastfood.shp")
tpe_county <- st_read("C:/Users/User/Downloads/20260228/Taipei_Vill.shp",options="ENCODING=Big5")
```

## Selecting McDonalds(no Trump)
This ensures that we are only dealing with Mcdonalds(`fastfood`), not all of the fastfood stores(`fastfood_all`).
```{r}
index = fastfood_all$STORE == "MIC"
fastfood = fastfood_all[index, ]
```

## chainstore(d) function

Note that in the following sections, we will be using the function `chainstore(d)` to construct chain density according to different distances.

```{r}
# Setting column names for better understanding
names(fastfood)[names(fastfood) == "ID"] = "fastfood_id"

chainstore = function(d){
  
  # Setting unit for distance
  d_km = set_units(d, km)
  
  # Using st_buffer to create buffer zones
  food_buf = st_buffer(fastfood, dist = d_km)  # Polygon of the buffers
  names(food_buf)[names(food_buf) == "fastfood_id"] = "polygon_id"
  
  # Spatial join to count fast food points within buffers
  joined_fastfood = st_join(fastfood, food_buf, join = st_within)
  joined_fastfood_df = as.data.frame(joined_fastfood)
  
  # Calculating density
  total = length(joined_fastfood_df$polygon_id) # Total fast food points in polygons
  density = total / nrow(fastfood)  # Average fast food points per polygon
  
  return(density)
}
```

## Plotting

The line chart is drawn by connecting the 7 points (setting `param` to 0~3 with difference of 0.5 and corresponding chainstore(d))
```{r}
# Setting up data frame
param = seq(0,3,0.5)
plot_df = data.frame( "x" = param, "y" = c(0,0,0,0,0,0,0))
for (i in 1:7){
  plot_df$y[i] = chainstore(param[i])
}

# Plotting
library(ggplot2)
ggplot(plot_df, aes(x, y)) +
  geom_line() + 
  xlab("服務半徑") +
  ylab("平均麥當勞的連鎖密度") +
  scale_y_continuous(breaks = seq(0, max(plot_df$y), by = 5)) 

```

## Question 2

比較A區(文山+大安+中正)與B區(信義+南港+松山)的麥當勞連鎖密度：
利用統計檢定方法，評估A區的平均每家麥當勞連鎖密度是否顯著高於B區。(服務半徑(d) = 1.5 km)
 (需列出虛無假設與對立假設，並說明檢定的顯著水準)。

## Selecting A region and B region
A區：文山、大安、中正、B區：信義、南港、松山。我們藉由`tpe_county`的資料做spatial join，得知麥當勞在哪個區。
```{r}
# Spatial Join
joindis_fastfood = st_join(fastfood, tpe_county, join = st_within)

# defining region index
regionA_index = joindis_fastfood$TOWN == "文山區"|joindis_fastfood$TOWN == "大安區"|joindis_fastfood$TOWN == "中正區"
regionB_index = joindis_fastfood$TOWN == "信義區"|joindis_fastfood$TOWN == "南港區"|joindis_fastfood$TOWN == "松山區"

# selecting region
regionA = joindis_fastfood[regionA_index, ]
regionB = joindis_fastfood[regionB_index, ]
```

## Setting a local chainstore function
Here, I try to make regions a parameter of the previous `chainstore` function. Notice the change in `function(d, region)`. With this, we can set the data to `results_regionA` and `results_regionB`.
```{r}

chainstore_region = function(d, region){
  # Setting unit for distance
  d_km = set_units(d, km)
  
  # Using st_buffer to create buffer zones
  food_buf = st_buffer(region, dist = d_km)  # Polygon of the buffers
  names(food_buf)[names(food_buf) == "fastfood_id"] = "polygon_id"
  
  # Spatial join to count fast food points within buffers
  joined_fastfood = st_join(fastfood, food_buf, join = st_within)
  joined_fastfood_df = as.data.frame(joined_fastfood)

  # Calculate how many MC in each polygon
  result = table(joined_fastfood_df$polygon_id) # table() calculates the numbers of different types of a column
  return(result)
}

# setting the variables
results_regionA = chainstore_region(1.5, regionA)
results_regionB = chainstore_region(1.5, regionB)
```
## Doing t-test
The setting are as follows:
Null hypothesis($H_{0}$): $\mu_{A} \leq \mu_{B}$; Alternative hypothesis($H_{1}$): $\mu_{A} > \mu_{B}$; Confidence level: 0.05; Hence, in the code we set `alternative = "greater"`
```{r}
t.test(results_regionA, results_regionB, alternative="greater") # one tailed test
```
As p-value =  0.729 suggests, we do not reject $H_{0}$. As a result, the average chain density of McDonalds in region A is not greater than that in region B.