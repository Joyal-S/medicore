from django.shortcuts import render
import math

# Create your views here.
def add(request):
    if request.method=="POST":
        a=request.POST.get("no1")
        b=request.POST.get("no2")
        c=int(a)+int(b)
        return render(request,'Basics/Add.html',{'result':c})
    else:
     return render(request,'Basics/Add.html')
def largest  (request):
    if request.method=="POST":
        a=request.POST.get("no1")
        b=request.POST.get("no2")
        if(a<b):
         c=b
        else:
         c=a
        return render(request,'Basics/Largest.html',{'result':c})
    else:
        return render(request,'Basics/Largest.html')

def RankList(request):
    if request.method=="POST":
        name=request.POST.get("txtname")
        gender= request.POST.get('radio')
        department= request.POST.get('seldept')
        mark1= int(request.POST.get('mark1'))
        mark2= int(request.POST.get('mark2'))
        mark3= int(request.POST.get('mark3'))

        total=mark1+mark2+mark3
        percentage = (total / 300) * 100

        if percentage >= 90:
            grade = "A"
        elif percentage >= 75:
            grade = "B"
        elif percentage >= 50:
            grade = "C"
        else:
            grade = "D"

        result ={
            'name':name,
            'gender':gender,
            'department':department,
            'mark1':mark1,
            'mark2':mark2,
            'mark3':mark3,
            'total':total,
            'percentage':round(percentage, 2),
            'grade':grade,
        }
        return render(request,'Basics/RankList.html',result)


    return render(request,'Basics/RankList.html')
def amstrong(request):
    result = ""
    if request.method == "POST":
        try:
            # Get the number from the form
            number = int(request.POST.get("txtno"))
            
            # Find the number of digits
            num_digits = len(str(number))
            temp = number
            sum_of_powers = 0
            
            # Calculate the sum of powers of each digit
            while temp > 0:
                remainder = temp % 10
                sum_of_powers += int(math.pow(remainder, num_digits))  # Raise each digit to the power of num_digits
                temp //= 10

            # Check if the sum of powers equals the original number
            if sum_of_powers == number: 
                result = f"{number} is an Armstrong number."
            else:
                result = f"{number} is not an Armstrong number."
        except ValueError:
            result = "Please enter a valid number."

        return render(request, 'Basics/Amstrong.html', {'result': result})
    return render(request,'Basics/Amstrong.html')