from more_itertools import distinct_permutations

def generate_layer_orders(max_ncompute):
	order_list=[]
	for ncompute in range(1,max_ncompute+1):
		for memscalar in range(5,8):
			seed_list=['2' for i in range(0,ncompute)]+['3' for i in range(0,ncompute*memscalar)]
			for p in distinct_permutations(seed_list):
				order_list.append(''.join(p))
	return order_list




if __name__ == "__main__":
	order_list=generate_layer_orders(max_ncompute=3)
	#order_list=permutation([1,2,2,3])
	#order_list=allLexicographicRecur([1,2,2,3], [], last, index)
	print(order_list)
	print(len(order_list))
