# -*- coding: utf-8 -*-
"""
Created on Wed May 13 09:59:28 2020

@author: sattwik, priyanka, prem, mansi
"""

'''
QUESTION:
    We are given 10 outlets j = 1, 2... 10, and warehouse j = 0 in France.
    Set of all products sold by the company is also given.
    Time horizon is considered 2/4 weeks.
    We know the demand D<jt> for 4 subsequent week (week t = current week, week t+1, week t+2 and week t+4) 
    at every outlet j for each product. This is a result of forecasting carried out over past 3 years demand data.
    We know the stock at each outlet j = S<jt> for week t and all products p.
    We know the distance x between all centres to compute the cost of transportation.
    Every week we run a decision model once to replenish the inventory at each outlet in two ways:
    1. From the warehouse, where the lead time is one week => products ordered today will arrive next week.
    2. Rebalancing from other outlets, where lead time is zero => products ordered today arrive immediately.
    The warehouse and the outlets have no capacity constraints. The arcs also have no capacity constraints.
    For material stored at the outlets we have identical inventory holding costs H.
    For Transportation Cost G we assume a dependence on the distance and amount of material transported on each arc
    We need to model this and at the beginning of each week determine what quantity of each product is to be
    rebalanced between the outlets and how much has to be ordered from the warehourse for each outlet
    so that the overall cost is minimized.
    We do the optimisation for only a particular product for all the ten outlets.
   
IDEA OF SOLUTION:
    We define a dynamic model where over four weeks we model the flow through the network.
    
FURTHER WORK TO BE DONE:
    Dinp = demand for all 10 outlets for 4 subesequent weeks will be generated from the forecasting program
    T = time horizon will be extended to compute model for both 2 and 4 weeks and material movement and loss sales will be compared
    Program will be run for all 10 outlets instead of three currently.
    Program will be extended to include uncertainities owing to demand forecasting.
'''


import math
import csv

from gurobipy import *
model = Model("Barkawi")


'''
PARAMETERS:
    Defining the nodes = I = [0, 1, 2, ...10]
    Defining the time steps= T = [0,1]
    Define the Vertices of the graph V = {(t,i) | for all t in T and all i in I}
    Define the arcs of the graph A = {(t,i,j) | for all t in T, i in I and j in I\{0}}
    Defining the Demands = D[t][i] for all i in I and all t in T
    Defining the Stock = O[i] for each outlet i in I\{0}
    0th node is the warehouse.
    Define the material movement on each arc w[t][i][j] for all i in I, j in I\{0}, t in T and i!=j
    Define the different costs pertaining to Transportation cost, Inventory Holding costs and lost sales costs 
    Assign costs to each of the arcs for unit material transported on the arcs and stored at an outlet 
'''

I = [0,1,2,3,4,5,6,7,8,9,10]    #Nodes = Warehouses + Outlets

T = [0,1]   #optimisation over time horizon of 2 weeks

#Demand at all 3 outlets over the two following weeks-> This would be an input Array
with open('J:\MMM_Data\demand_forecast_2_week4.csv', newline='') as csvfile:
    Dinp = list(csv.reader(csvfile))

for i in range(10):
    for j in range(2):
        Dinp[i][j]=math.ceil(float(Dinp[i][j]))

#Arranging demand array into a MATRIX with usable indices
DEM = {}
for t in T:
    for i in I:
        if i!=0:                        #Demand is not defined for the warehouse
            DEM[t, i] = Dinp[i-1][t]       


#Demand D for outlets at different times D[t][j]. Vertices V are thus defined as (t,i) for all t        
V, D = gurobipy.multidict(DEM)    


#Stock left over from week '-1', week before the order week t=0: This would be an input Array
with open('J:\MMM_Data\outlet_stock_next.csv', newline='') as csvfile:
    Oinp = list(csv.reader(csvfile))

O=[]
for i in range(10):
    O.append(math.ceil(float(Oinp[0][i])))
        


#replenishment from Warehouse arriving at starting of week t=0: This would be an input Array
with open(r'J:\MMM_Data\replenishment_next.csv', newline='') as csvfile:
    Rinp = list(csv.reader(csvfile))
R=[]
for i in range(10):
    R.append(math.ceil(float(Rinp[0][i])))
       

#Transport cost per dist per quantity transferred
GO = 0.08
GW = 0.06       

#Inventory holding cost per unit inventory: 5% of cost of the product 
H = 0.79  

#Cost incurred due to loss of sales: margin on the product = 30% of cost of product   
U = 591       

#MOQ of the item- Input from User
Q=25       

# MAX CAPACITY value for each arc for relating decision variable to quantity variable for each arc = max(demand) + MOQ
M = 1*(Q + max(max(Dinp)))   

#Distance matrix: it is symmetric
with open('J:\MMM_Data\distance_matrix.csv', newline='') as csvfile:
    distinp = list(csv.reader(csvfile))

x=[]
location=[]
for i in range(11):
    location.append(distinp[i+1][0])
    x.append([])
    for j in range(11):
        x[i].append(float(distinp[i+1][j+1]))


#decision matrix to define the cost of each arc
COST = {}
for t in T:                                 
    for i in I:
        for j in I:                               
            if i!=0 and j!=0:
                if i!=j:
                    COST[t,i,j] = x[i][j]*GO
            if i==0 and j!=0:
                COST[t,i,j] = x[i][j]*GW + H


#Definition of each arc in A and Cost C of each arc which includes inventory holding cost + transportation cost
A, C = gurobipy.multidict(COST)  

#decision matrix to define the inventory holding cost for left over stock after each week at each vertex
INV = {}
for t in T:
    for i in I:
        if i!=0: 
            if t==T[-1]:                       #Inventory holding cost is only incurred by the inventory left over in the end of last week
                INV[t, i] = H
            else:
                INV[t, i] = 2*H
            
#inventory holding cost over left over stock = K[t][j]. Vertices V are thus defined as (t,i) for all t        
V, K = gurobipy.multidict(INV)  


'''
VARIABLES:
    w[a] = amount of goods carried on each arc, for all a in A
    l[V] = loss of sales at each outlet, for all v in V
    y[A] = if arc is chosed or not, for all a in A
    s[V]= stock at the end of each week not sold at the outlet, for all v in V
'''

w = model.addVars(A, lb =0, obj=C, vtype= GRB.INTEGER, name="arc_quantity")
l = model.addVars(V, lb=0, obj=U, vtype= GRB.INTEGER, name="lost_sales")
y = model.addVars(A, obj=0, vtype= GRB.BINARY, name="arc_select")
s = model.addVars(V, lb=0, obj=K, vtype= GRB.INTEGER, name="stock")


'''
CONSTRAINTS:
    Constraints assigning initial conditions to variables in week 0
    Demand constraint for all outlets
    MOQ constraints for shipment from Warehouse
    arc selection constraint linking w and y
'''


#Replenishment from the warehouse in Week t needs to be assigned as per input array R
for j in I[1:]:
    if (0,0,j) in A:
        model.addConstr((w[0,0,j]>=R[j-1]), "from_warehouse_t0_greater")
        model.addConstr((w[0,0,j]<=R[j-1]), "from_warehouse_t0_smaller")
                

#Demand constraints for week t (T equations)
model.addConstrs((O[j-1] + w.sum(0, '*',j) - w.sum(0, j, '*') >= D[0,j] - l[0,j] for j in I[1:]), "demand_t=0")
model.addConstrs((s[t-1,j] + w.sum(t, '*',j) - w.sum(t, j, '*') >= D[t,j] - l[t,j] for j in I[1:] for t in T[1:] ), "demand_t")                           


#Stock at the end of week t (T equations)
model.addConstrs((s[0, j] >= O[j-1] + w.sum(0, '*',j) - w.sum(0, j, '*') - D[0,j] +l[0,j] for j in I[1:]), "demand_t=0greater")                          
model.addConstrs((s[0, j] <= O[j-1] + w.sum(0, '*',j) - w.sum(0, j, '*') - D[0,j] +l[0,j] for j in I[1:]), "demand_t=0lesser")                          
model.addConstrs((s[t, j] >= s[t-1,j] + w.sum(t, '*',j) - w.sum(t, j, '*') - D[t,j] +l[t,j] for j in I[1:] for t in T[1:]), "demand_tgreater")                          
model.addConstrs((s[t, j] <= s[t-1,j] + w.sum(t, '*',j) - w.sum(t, j, '*') - D[t,j] +l[t,j] for j in I[1:] for t in T[1:]), "demand_tlesser")                          


#MOQ constraints
model.addConstrs((w[t,0,j]>=Q*y[t,0,j] for j in I[1:] for t in T), "MOQ")

#y constraints
model.addConstrs((w[t,i,j]<=M*y[t,i,j] for (t,i,j) in A), "x_y_relationship")


'''
SOLVE THE MODEL:
'''

model.optimize()

'''
PRINTING THE SOLUTION:
'''
TotalCost=0
TotalCostWeek1=0
if model.status == GRB.OPTIMAL:
    print("\nRESULT:\n")
    for t in T:        
        for i in I:
            for j in I:
                if (t,i,j) in A:
                    if w[(t,i,j)].x:
                        print(f"{(w[t,i,j].x)} quantity of the product is transferred from {location[i]} to {location[j]} in week {t}")
                        TotalCost = TotalCost + math.ceil(w[t,i,j].x)*C[t,i,j]
                        
                        if t==0:
                            TotalCostWeek1 = TotalCostWeek1 + math.ceil(w[t,i,j].x)*C[t,i,j]
                        #print(TotalCost)
    cnt=0
    for t in T:        
        for i in I:
            if (t,i) in V:
                if l[(t,i)].x:
                    print(f"{(l[t,i].x)} is the loss of sales at {location[i]} in week {t}")
                    cnt=cnt+1
                    TotalCost = TotalCost + (l[t,i].x)*U
                    if t==0:
                        TotalCostWeek1 = TotalCostWeek1 + (l[t,i].x)*U
                if s[(t,i)].x:
                    #print(f"{(s[t,i]).x} is the inventory left after week {t}")
                    TotalCost = TotalCost + (s[t,i].x)*K[t,i]
                    if t==0:
                        TotalCostWeek1 = TotalCostWeek1 + (s[t,i].x)*K[t,i]
                #print(TotalCost)
    if cnt==0:
        print("\nThere is no loss of sales")
        
    #for i in range(10):
        #TotalCost = TotalCost + O[i]*H
        
    print(f"\nThe total cost of replenishment and rebalancing for a 2 week time horizon is {round(model.objval,2)}")
    print(f"\nThe total cost of replenishment and rebalancing for 1st week  is {round(TotalCostWeek1,2)}")
    print(f"\nThe runtime of the model is {round(model.Runtime,2)}seconds")
else:
    print("\n\nRESULT:\nNo solution could be obtained for given preferences")
    

#Printing the values of the w variable into a csv file for importing into uncertain file

REPLW=[]
for t in T:                                 
    for i in I:
        for j in I:                               
            if (t,i,j) in A:
                REPLW.append(w[(t,i,j)].x)
                
                        
import csv
with open("J:\MMM_Data\Deterministic_transshipment.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerows([REPLW])   

'''
REPL=[]
STOCK=[]

for j in I:
    if j!=0:
        if (1,0,j) in A:
            REPL.append(w[1,0,j].x)
            
for j in I:
    if j!=0:
        if (0,j) in V:
            STOCK.append(s[0,j].x)
            
                           
import csv
with open(r"J:\MMM_Data\replenishment_next.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerows([REPL]) 
with open("J:\MMM_Data\outlet_stock_next.csv", "w") as g:
    writer = csv.writer(g)
    writer.writerows([STOCK]) 
'''