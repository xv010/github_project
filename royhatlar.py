A = [22, 14, 45, 64, 9]

juft_sonlar = []
toq_sonlar = []

for item in A:
    if type(item) == int:
        if item % 2 == 0:
            juft_sonlar.append(item)
        else:
            toq_sonlar.append(item)
print("Juft sonlar:", juft_sonlar)
print("Toq sonlar:", toq_sonlar)
