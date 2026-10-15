class MASDFAB26:
    """
    This class represents the MAS DFAB 26/27 module for Git introduction.
    """

    def __init__(self):
        self.Name = "MASDFAB26"
        self.Tutors = ['Ananya', 'Chewei'] 
        self.Coolest_Tutor = 'Pineapple' #Change to 'Ananya' if you think Ananya is the coolest tutor
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

    def Ananya(self):
        print(f"Hi, I am Pineapple, {"the coolest tutor" if self.Coolest_Tutor == 'Ananya' else "the second cool tutor"}!\n")

    def James(self):
        print("Hi, I am James, cnc cowboy. Yeehaw!")
    
    def YOUR_NAME_IN_SELF_STUDENTS(self):
        """
        Add a method of your name in the student list, and print your self introduction.
        """
        print("Hi, Hungry. I'm Dad")


if __name__ == "__main__":
    mas = MASDFAB26()   
    mas.introduction()