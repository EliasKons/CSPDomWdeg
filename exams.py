import csp
import pandas as pd
import time


class Exams(csp.CSP):
    """
    The exam period lasts for 21 continuous days and each day has 3 time slots (9-11, 11-1, 
    11-3). The information for each subject can be accessed from a csv. Each subject has a 
    semester number, a proffessor name, an indication true/false whether the subject is difficult 
    or not, and another indication true/flase whether the subject has an extra lab or not. The 
    constraints of the CSP are:
    - No more than one subject can have the same day and time slot
    - The lab exam of a subject (if the subject has a lab) should be held exactly after the exam
      of the subject itself
    - The exams for the subjects of the same year should be held in different days
    - The exams of the subjects of the same professor should be held in different days
    - The exams of the difficult subjects should be held at least 2 days apart
    """

    def __init__(self, csv):
        data = pd.read_csv(csv)
        subjects = data['Subject'].tolist()
        self.semesters = dict(zip(subjects, data['Semester'].tolist()))
        self.professors = dict(zip(subjects, data['Professor'].tolist()))
        self.difficulties = dict(zip(subjects, data['Difficult (TRUE/FALSE)'].tolist()))
        check_lab = dict(zip(subjects, data['Lab (TRUE/FALSE)'].tolist()))

        self.variables = []
        self.laboratories = {}

        for subject in subjects:
            if check_lab[subject]:
                theory = subject + ' Theory'
                lab = subject + ' Lab'
                self.variables.extend([theory, lab])
                self.laboratories[lab] = theory
                self.semesters[theory] = self.semesters.pop(subject)
                self.professors[theory] = self.professors.pop(subject)
                self.difficulties[theory] = self.difficulties.pop(subject)
            else:
                self.variables.append(subject)

        self.domains = {var: [(i, j) for i in range(21) for j in range(3)] for var in self.variables}
        self.neighbors = {var: [sub for sub in self.variables if sub != var] for var in self.variables}

        self.var_to_cons = {var: [self.slot_constraint] for var in self.variables}
        for var in self.variables:
            if var in self.laboratories or var in self.laboratories.values():
                self.var_to_cons[var].append(self.lab_constraint)
            if var not in self.laboratories:
                self.var_to_cons[var].extend([self.semester_constraint, self.professor_constraint])
                if self.difficulties[var]:
                    self.var_to_cons[var].append(self.difficulty_constraint)

        super().__init__(self.variables, self.domains, self.neighbors, 
                         (self.slot_constraint, self.lab_constraint, self.semester_constraint, 
                          self.professor_constraint, self.difficulty_constraint), self.var_to_cons)

    def slot_constraint(self, A, a, B, b):
        return a != b

    def lab_constraint(self, A, a, B, b):
        if A in self.laboratories and self.laboratories[A] == B:
            return a[0] == b[0] and a[1] == b[1] + 1
        if B in self.laboratories and self.laboratories[B] == A:
            return b[0] == a[0] and b[1] == a[1] + 1
        return True

    def semester_constraint(self, A, a, B, b):
        return self.semesters[A] != self.semesters[B] or a[0] != b[0]

    def professor_constraint(self, A, a, B, b):
        return self.professors[A] != self.professors[B] or a[0] != b[0]

    def difficulty_constraint(self, A, a, B, b):
        return abs(a[0] - b[0]) >= 2

    def display(self, assignment):
        DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        SLOTS = ['9-11', '11-1', '1-3']
        WEEKS = ['First Week', 'Second Week', 'Third Week']

        for k in range(3):
            print(WEEKS[k])
            for i in range(k * 7, (k + 1) * 7):
                print(DAYS[i % 7])
                for j in range(3):
                    for subject, (day, slot) in assignment.items():
                        if (i, j) == (day, slot):
                            print(f'{SLOTS[j]}: {subject}', end='\t')
                print()
            print()



if __name__ == '__main__':
    exams = Exams('subjects.csv')

methods = [
    ('FC + MRV:', csp.mrv, csp.forward_checking),
    ('FC + DOM/WDEG:', csp.dom_wdeg, csp.forward_checking),
    ('MAC + MRV:', csp.mrv, csp.mac),
    ('MAC + DOM/WDEG:', csp.dom_wdeg, csp.mac),
    ('MIN_CONFLICTS:', None, None)
]

for name, var_selector, inference in methods:
    print('--------------------')
    print(name)
    start = time.time()
    if name == 'MIN_CONFLICTS:':
        result, constraint_checks, visited_nodes = csp.min_conflicts(exams)
    else:
        result, constraint_checks, visited_nodes = csp.backtracking_search(
            exams, select_unassigned_variable=var_selector,
            order_domain_values=csp.lcv, inference=inference
        )
    end = time.time()
    print(f'\nExecution time: {end - start:.5f} Seconds')
    print('Number of visited nodes:', visited_nodes)
    print('Number of consistency checks:', constraint_checks, '\n')
    exams.display(exams.infer_assignment() if name != 'MIN_CONFLICTS:' else result)
