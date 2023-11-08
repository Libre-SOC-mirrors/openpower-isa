#include<stdio.h>
#include<limits.h>
//#include<cornio.h>
int m2(int * const restrict a, int n) 
{ 
	int m, nm; 
  	int i; 

 	m = INT_MIN; 
    	nm = -1; 
    	i=0; 
	while (i<n) { 
		while (i<n && a[i]<=m) 
            		i++; 
        	if (a[i] > m) { 
            		m = a[i]; 
            		nm = i; 
        	} 
        	i++; 
    	} 
    	return nm; 
}

/*Testbench*/

int main() 
{

	int arr[]= {5,2,8,1,3,7,9,4};
	int size = sizeof(arr) / sizeof(arr[0]);
	int result = m2(arr, size);

	printf("Index of the maximum value in an array is: %d\n", result);
	return 0;

}
