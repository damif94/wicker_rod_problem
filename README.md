# Wicker Rod Problem
An Integer Programming Solver for The Wicker Rod Optimization Problem

To manufacture a wicker rattan box, m1 pieces of length l1, m2 pieces of length l2 and m3 pieces of length l3 are needed. 
For that, rods of length l are provided. The goal of the producer is to find a batch size and the "recipe" that will allow the production of that batch while minimizing the absolute wicker waste.

# Theoretical development
Can be found on `theory.pdf`.
It's divided in the following sections:
1. Introduction: A basic, non technical introduction to the problem
2. Formalization and formulation: The necessary notions are formalized and the problem is formulated mathematically using this notions
3. Formulations as an IP problem: An Integer Programming equivalent version of the problem in section 2 is formulated.
4. Implementation details: Where some implementation caveats are explained

# Implementation
The whole implementation can be found under `solver.py`. This solver is basically an adapter script on top of the python port for the [IBM CPLEX](https://www.ibm.com/analytics/cplex-optimizer) solver for Integer Programming problems.

# Instructions to run
Assuming that you have python3 and pip3 installed in your system, running the solver is pretty simple:
Start by downloading the CPLEX port by executing on a terminal
```python 
pip3 install cplex
```

Then you can run the solver with the desired parameters 
```python 
python3 solver.py l l1 l2 l3 m1 m2 m3 n_bound
```
where `l` is the rod length, `l1 > l2 > l3` are the manufacturing lengths, `m1, m2, m3` are the manufacturing multiplicities 
and the best solution found using a batch size of at most `n_bound` will be printed into STDOUT.

# Running example
The following screenshot shows the output for the original problem's parameters, that motivated this development.

<img width="528" alt="Screen Shot 2022-05-04 at 19 36 51" src="https://user-images.githubusercontent.com/29461526/166746623-7574eabf-c1c8-430e-91c9-5de2a5754b90.png">

