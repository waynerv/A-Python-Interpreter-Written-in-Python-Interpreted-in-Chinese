# 用Python实现一个简单解释器

what_to_execute = {
    "instructions": [("LOAD_VALUE", 0),  # the first number
                     ("LOAD_VALUE", 1),  # the second number
                     ("ADD_TWO_VALUES", None),
                     ("PRINT_ANSWER", None)],
    "numbers": [7, 5]}


class Interpreter():
    def __init__(self):
        self.stack = []

    def LOAD_VALUE(self, number):
        self.stack.append(number)

    def PRINT_ANSWER(self):
        answer = self.stack.pop()
        print(answer)

    def ADD_TWO_VALUES(self):
        first_num = self.stack.pop()
        second_num = self.stack.pop()
        total = first_num + second_num
        self.stack.append(total)

    def run_code(self, what_to_execute):
        instructions = what_to_execute['instructions']
        numbers = what_to_execute['numbers']
        for instruction, argument in instructions:
            # instructions, argument = each_step
            if instruction == 'LOAD_VALUE':
                number = numbers[argument]
                self.LOAD_VALUE(number)
            elif instruction == 'ADD_TWO_VALUES':
                self.ADD_TWO_VALUES()
            elif instruction == 'PRINT_ANSWER':
                self.PRINT_ANSWER()

interpreter = Interpreter()
interpreter.run_code(what_to_execute)