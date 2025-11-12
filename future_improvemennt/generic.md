the mistake that many people makes when trying to create models to predict stocks is that they mistakebnly assume that to predict stock prices for tomorrow, they should train their model on daily price movements, WHY ? . this makes no sense. it is just a bunch of numbers at this time with almost no relationship. 

here is my solution - you should train your model on minute by minute data - from the previous day , then hourly data from the previous day, each leading to the next day opening price. 

your model will have an idea of why the previous day price leads to the next days opening price. 

it will have internally build a relationship between this prices. 

if you are just taking opening and closing prices for each day - then your model cant predict the next day price because well it cant see what happens in between to lead to the new price. there is no relationship buildup, your model is not even aware at this point that prices goes up in very small intervals.