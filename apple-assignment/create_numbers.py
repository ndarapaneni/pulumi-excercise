with open("/home/ec2-user/numbers.txt","w") as file:
  for number in range(1,101):
    file.write(f"{number}\n")
