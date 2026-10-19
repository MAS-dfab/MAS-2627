class MASDFAB26:
    """
    This class represents the MAS DFAB 26/27 module for Git introduction.
    """

    def __init__(self):
        self.Name = "MASDFAB26"
        self.Tutors = ['Ananya', 'Chewei'] 
<<<<<<< Updated upstream
        self.Coolest_Tutor = 'Pineapple' #Change to 'Ananya' if you think Ananya is the coolest tutor
=======
        self.Coolest_Tutor = 'Chewei Lin' #Change to 'Ananya' if you think Ananya is the coolest tutor
>>>>>>> Stashed changes
        self.students = ('Eliot', 'Daniel', 'Despoina', 'Ishant', 'Jiaqi', 'Devin', 'Nikitha', 'Adam', 'James', 'Pasathorn', 'Nils', 'Naz', 'Yuanyao', 'Michael', 'Athina', 'Jaewon', 'Haerin', 'Weijiun')

    def introduction(self):
        intro = f"Welcome to {self.Name} a class of {len(self.students)} students!\n\nTutors: {', '.join(self.Tutors)}.\n\nStudents: {', '.join(self.students)}.\n"
        print (intro)

        # tutor introduction
        if hasattr(self, 'Ananya'):
            getattr(self, 'Ananya')()

        print ("The students will now introduce themselves\n")

        # check if class has the function with student name
        for student in self.students:
            if hasattr(self, student):
                getattr(self, student)()
            else:
                print (f"{student} is not in the cluster.")

    def Pasathorn(self):
        print("Halo, I am Pasathorn")

    def Ananya(self):
<<<<<<< Updated upstream
        print(f"Hi, I am Pineapple, {"the coolest tutor" if self.Coolest_Tutor == 'Ananya' else "the second cool tutor"}!\n")

    def James(self):
        print("Hi, I am James, cnc cowboy. Yeehaw!")
=======
        print(f"Hi, I am Ananya, {"the greatest tutor" if self.Coolest_Tutor == 'Ananya' else "the second cool tutor"}!\n")
>>>>>>> Stashed changes
    
    def Ishant(self):
        
        tutor_status = "agreeing with Chewei" 
        print(f"Hi, I am Ishant, currently {tutor_status} on who the coolest tutor is!\n")


    def Nikitha(self):
        print("Hi, Im Nikitha")

    def Devin(self):
        print(f"Hallo, ich heisse Devin")

<<<<<<< Updated upstream
    def Jaewon(self):
        print("Jaewon Song~ Sing a Song~ La La La~~")

    def Weijiun(self):
       print("6767676767676767676767667")

    def Eliot(self):
        print("Hi, I'm Eliot. I'm here, and I definitely did not use AI to write this.\n")

    def Daniel(self):
        print("Hola, soy Daniel. A ver si esto funciona")
=======
    def Daniel(self):
        print("Hi, Mommy. I'm Daddy")

>>>>>>> Stashed changes

if __name__ == "__main__":
    mas = MASDFAB26()   
    mas.introduction()
