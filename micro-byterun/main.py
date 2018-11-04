import dis, sys, collections, operator, types, inspect


Block = collections.namedtuple("Block", "type, handler, stack_height")


class VirtualMachineError(Exception):
    """定义在VirtualMachine的操作中唤起的异常"""
    pass

class VirtualMachine(object):
    def __init__(self):
        self.frames = []  # 调用栈
        self.frame = None  # 当前帧
        self.return_value = None  # 在帧之间传递的返回值
        self.last_exception = None  # 上一个异常

    def run_code(self, code, global_names=None, local_names=None):
        """
        这里是使用VirtualMachine执行代码的入口
        以编译后的代码对象为参数，创建一个帧，并开始运行
        参数中的全局命名空间和局部命名空间默认值均为None
        """
        frame = self.make_frame(code, global_names=global_names,
                                local_names=local_names)
        self.run_frame(frame)

    # 对帧的操作
    def make_frame(self, code, callargs={}, global_names=None, local_names=None):
        """
        创建新的帧的方法，并为新的帧找到命名空间
        参数为代码对象，调用参数字典，全局命名空间和局部命名空间
        """
        # 如果全局命名空间和布局变量都不为空，即传入代码对象指定了全局命名空间和局部命名空间时
        if global_names is not None and local_names is not None:
            local_names = global_names  # 全局名称空间下，局部名称空间就是全局空间（即没有函数执行时）
        elif self.frames:  # 已存在当前帧时创建新的下一帧时
            global_names = self.frame.global_names  # 当前帧的全局命名空间引入创建的下一帧作为全局命名空间
            local_names = {}  # 所创建的下一帧的局部空间为空
        else:  # 既不存在当前帧也未给定全局命名空间和局部命名空间时，即在模块中首次创建帧时
            # 为全局命名空间和局部命名空间设置默认值，并引入内建模块的命名空间
            global_names = local_names = {
                '__builtins__': __builtins__,  # __builtins__是对内建模块的引用，引入了内建的函数、变量、类等标识符与对应对象
                '__names__': '__main__',
                '__doc__': None,
                '__package__': None,
            }
        local_names.update(callargs)  # 将函数调用时传递的参数映射合入局部命名空间
        # 实例化Frame类，创建新的帧及帧内对应的属性，将当前帧作为对上一帧的引用参数传入
        frame = Frame(code, global_names, local_names, self.frame)
        return frame

    def push_frame(self, frame):
        """压入帧，将通过参数传递的帧对象加入调用栈顶部，并将其置为当前帧"""
        self.frames.append(frame)
        self.frame = frame

    def pop_frame(self):
        """弹出帧，将调用栈顶部的帧弹出，并将当前帧置为当前调用栈顶部的帧，如果没有则为None"""
        self.frames.pop()
        if self.frames:
            self.frame = self.frames[-1]
        else:
            self.frame = None

    def run_frame(self, frame):
        """
        运行给定的帧直到帧返回值
        能够唤起异常，将返回值返回
        """
        self.push_frame(frame)  # 将帧压入调用栈顶部
        while True:  # 以指令组为单位循环处理代码对象中的指令
            byte_name, arguments = self.parse_byte_and_args()  # 解析当前帧的代码对象，返回指令名称和参数

            why = self.dispatch(byte_name, arguments)  # 执行指令，返回why标志信息

            # 处理我们需要进行的块（block）操作
            while why and frame.block_stack:  # 当why有返回值且块栈不为空
                why = self.manage_block_stack(why)  # 执行块操作并返回

            if why:  # 当块栈的返回值不为0或None时，跳出循环，停止处理指令
                break

        self.pop_frame()  # 弹出帧，重置当前帧

        if why == 'exception':  # 如果指令处理过程中捕获到了异常，解析异常信息
            exc, val, tb = self.last_exception  # last_exception解析为(type, value, None)
            e = exc(val)  # 解析异常类型
            e.__traceback__ = tb  # 构建异常回溯信息
            raise e  # raise异常类型

        return self.return_value  # 返回所运行帧的返回值

    # 数据栈的操作
    def top(self):
        return self.frame.stack[-1]  # 返回数据栈顶部的对象

    def pop(self):
        return self.frame.stack.pop()  # 弹出数据栈顶部的对象

    def push(self, *vals):
        self.frame.stack.extend(vals)   # 将给定对象压入数据栈顶部

    def popn(self, n):
        """从数据栈顶部弹出多个对象，返回一个n个对象的列表，在数据栈中最底层的对象在列表最前面"""
        if n:
            ret = self.frame.stack[-n:]  # 弹出数据栈中后n个对象
            self.frame.stack[-n:] = []
            return ret
        else:
            return []

    def jump(self, jump):
        """移动读取指令的指针到接受的索引参数jump处，使被跳转目标在下一指令中执行"""
        self.frame.last_instruction = jump

    def parse_byte_and_args(self):
        """解析代码对象中的一组字节码"""
        f = self.frame  # 当前帧
        opoffset = f.last_instruction  # 指令指针初始值为0
        byteCode = f.code_obj.co_code[opoffset]  # 指令字节码
        f.last_instruction += 1
        byte_name = dis.opname[byteCode]  # 指令名称 dis.opname是字节码的指令集序列，可以用字节码（数字）来索引
        if byteCode >= dis.HAVE_ARGUMENT:  # 通过指令字节码判断指令是否有参数  < HAVE_ARGUMENT：无  >= HAVE_ARGUMENT：有
            # 解析指令参数
            arg = f.code_obj.co_code[f.last_instruction:f.last_instruction+2]  # 指令中后两个代表参数的字节码
            f.last_instruction += 2  # 后移读取指令的指针
            arg_val = arg[0] + (arg[1] * 256)  # 通过字节码计算参数索引
            if byteCode in dis.hasconst:  # 查找常量
                arg = f.code_obj.co_consts[arg_val]  # 取回常量参数
            elif byteCode in dis.hasname:  # 查找变量
                arg = f.code_obj.co_names[arg_val]  # 取回变量参数
            elif byteCode in dis.haslocal:  # 查找本地变量
                arg = f.code_obj.co_varnames[arg_val]  # 取回本地参数
            elif byteCode in dis.hasjrel:  # 计算关联跳转
                arg = f.last_instruction + arg_val  # 取回跳转目标的索引
            else:
                arg = arg_val  # 以上无法查找到则参数为arg_val字面值（整数）
            argument = [arg]  # 创建参数列表
        else:  # 不接收参数
            argument = []

        return byte_name, argument  # 返回指令名称和参数

    def dispatch(self, byte_name, argument):
        """
        通过给定的指令名称查找指令并执行相应的操作（方法）
        捕获异常并在VirtualMachine中处理
        """
        # 晚点当我们展开块栈，我们需要记录为什么我们要那么做
        why = None  # 指令方法执行后返回的额外标志信息
        try:
            bytecode_fn = getattr(self, f'byte_{byte_name}', None)  # 查找并取得指令名称对应的指令方法
            if bytecode_fn is None:  # 如果名称对应的指令方法不存在
                if byte_name.startswith('UNARY_'):  # 指令名称以‘UNARY_’开头
                    self.unaryOperator(byte_name[6:])
                elif byte_name.startswith('BINARY_'):  # 指令名称以‘BINARY_’开头
                    self.binaryOperator(byte_name[7:])
                else:
                    raise VirtualMachineError(
                        f"unsupported bytecode type:{byte_name}"
                    )
            else:
                why = bytecode_fn(*argument)  # 传递参数执行指令，返回why标志
        except:  # 捕获所有异常
            # 处理执行该指令时遇到的异常
            self.last_exception = sys.exc_info()[:2] + (None,)  # 记录通过sys模块获取的异常信息
            why = 'exception'

        return why

    # 块栈的操作
    def push_block(self, b_type, handler=None):  # 压入块栈，接受块类型和处理器参数
        stack_height = len(self.frame.stack)  # 当前数据栈的层数
        self.frame.block_stack.append(Block(b_type, handler, stack_height))  # 新增一个块对象Block（数据类型是namedtuple）

    def pop_block(self):  # 弹出块栈
        return self.frame.block_stack.pop()

    def unwind_block(self, block):  # 展开块栈，接受块对象（Block）为参数
        """Unwind the values on the data stack corresponding to a given block."""
        if block.type == 'except_handler':  # 判断块的类型是否为异常处理器
            # 异常以（type, value, and traceback）组成的元组形式存在于数据栈中
            offset = 3
        else:
            offset = 0

        # 当数据栈对象数量大于块栈的块的数量，弹出数据栈顶端的对象，直到数量相等(根据是否唤起异常比较条件不同）为止
        while len(self.frame.stack) > block.level + offset:
            self.pop()

        if block.type == 'except-handler':  # 判断块的类型是否为异常处理器
            traceback, value, exctype = self.popn(3)  # 从数据栈顶部弹出3个对象，分别对应异常的回溯记录、值、类型
            self.last_exception = exctype, value, traceback

    def manage_block_stack(self, why):
        """
        管理一个帧的块栈.
        操作块栈和数据栈实现循环、异常处理及返回等控制流
        """
        frame = self.frame  # 当前帧
        block = frame.block_stack[-1]  # 块栈顶部的块（Block）
        if block.type == 'loop' and why == 'continue':  # 当块的类型为loop，why的标志信息为continue
            self.jump(self.return_value)  # 移动当前指令指针到帧的返回值
            why = None  # 重置why标志信息
            return why

        self.pop_block()  # 弹出块栈顶部的块（block）
        self.unwind_block(block)  # 展开被弹出的块

        if block.type == 'loop' and why == 'break':  # 如果块的类型为loop，why的标志信息为break
            why = None  # 重置why标志
            self.jump(block.handler)  # 跳转至块中的处理器处（指定索引）
            return why

        if block.type in ['setup-except', 'finally'] and why == 'exception':  # 如果块的类型和why标志满足特定条件
            self.push_block('except-handler')  # 压入异常处理器类型的块到块栈
            exctype, value, tb = self.last_exception  # 解析异常信息
            self.push(tb, value, exctype)  # 将异常的回溯记录、值、类型分别压入数据栈顶部
            self.push(tb, value, exctype)  # 执行两次
            why = None  # 重置why标志
            self.jump(block.handler)  # 跳转至块中的处理器处（指定索引）
            return why

        elif block.type == 'finally':  # 如果块的类型为finally
            if why in ('return', 'continue'):  # why标志满足特定条件
                self.push(self.return_value)  # 将帧的返回值压入数据栈顶部

            self.push(why)  # 将why标志信息压入数据栈顶部

            why = None  # 重置why
            self.jump(block.handler)  # 跳转至块中的处理器处
            return why
        return why

    # 对数据栈的操作
    def byte_LOAD_CONST(self, const):  # 压入常量到数据栈顶部
        self.push(const)

    def byte_POP_TOP(self):  # 取出数据栈顶部的对象
        self.pop()

    # 变量
    def byte_LOAD_NAME(self, name):  # 压入变量到数据栈顶部
        frame = self.frame  # 当前帧
        # 以下展示了解释器中名称的查找顺序，即：局部命名空间-->全局命名空间-->内置命名空间
        if name in frame.local_names:  # 如果变量名称存在于局部命名空间，则取回变量对应的对象（与val绑定）
            val = frame.local_names[name]
        elif name in frame.global_names:
            val = frame.global_names[name]
        elif name in frame.builtins:
            val = frame.builtin_names[name]
        else:  # 如果找不到名称，唤起异常
            raise NameError(f"name {name} is not defined")
        self.push(val)  # 将变量对象压入数据栈

    def byte_STORE_NAME(self, name):  # 接受参数作为名称，弹出数据栈顶部的对象并存入局部命名空间（赋值给变量）
        self.frame.local_names[name] = self.pop()

    def bytes_LOAD_FAST(self, name):  # 压入局部变量到数据栈顶部
        if name in self.frame.local_names:  # 同上
            val = self.frame.local_names[name]
        else:
            raise UnboundLocalError(
                f"local variable {name} referenced before assignment"
            )  # 唤起局部名称未定义异常
        self.push(val)

    def byte_STORE_FAST(self, name):  # 赋值给局部变量
        self.frame.local_names[name] = self.pop()

    def byte_LOAD_GLOBAL(self, name):  # 压入全局变量到数据栈顶部
        f = self.frame
        if name in f.global_names:  # 首先从全局命名空间查找
            val = f.global_names[name]
        elif name in f.builtin_names:  # 然后从内置命名空间查找
            val = f.builtin_names[name]
        else:  # 唤起名称为定义错误
            raise NameError(f"global name {name} is not defined")
        self.push(val)  # 将变量对象压入数据栈

    # 操作符
    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT': operator.not_,
        'CONVERT': repr,
        'INVERT': operator.invert,
    }  # 一元操作符

    def unaryOperator(self, op):  # 定义操作符方法，直接调用python内置函数
        x = self.pop()
        self.push(self.UNARY_OPERATORS[op](x))  # 弹出操作数，操作或运算后将结果压入数据栈

    BINARY_OPERATORS = {
        'POWER':    pow,
        'MULTIPLY': operator.mul,
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE':  operator.truediv,
        'MODULO':   operator.mod,
        'ADD':      operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR':   operator.getitem,
        'LSHIFT':   operator.lshift,
        'RSHIFT':   operator.rshift,
        'AND':      operator.add,
        'XOR':      operator.xor,
        'OR':       operator.or_,
    }  # 二元操作符

    def binaryOperator(self, op):  # 定义操作符方法，直接调用python内置函数
        x, y = self.popn(2)
        self.push(self.BINARY_OPERATORS[op](x, y))  # 弹出操作数，操作或运算后将结果压入数据栈

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]  # 比较操作符

    def byte_COMPARE_OP(self, opnum):  # 定义操作符方法，直接调用python内置函数
        x, y = self.popn(2)
        self.push(self.COMPARE_OPERATORS[opnum](x, y))  # 弹出操作数，操作或运算后将结果压入数据栈

    # 属性和索引
    def byte_LOAD_ATTR(self, attr):  # 获取对象属性getattr
        obj = self.pop()
        val = getattr(obj, attr)
        self.push(val)

    def byte_STORE_ATTR(self, name):  # 保存对象属性setattr
        val, obj = self.popn(2)
        setattr(obj, name, val)

    # 构建
    def byte_BUILD_LIST(self, count):  # 构建列表
        elts = self.popn(count)  # 本身是以列表形式弹出
        self.push(elts)

    def byte_BULD_MAP(self, size):  # 构建空字典，忽略size参数
        self.push({})

    def byte_STORE_MAP(self):  # 指定3个对象构建字典
        the_map, val, key = self.popn(3)
        the_map[key] = val
        self.push(the_map)

    def byte_LIST_APPEND(self, count):  # 列表合并
        val = self.pop()
        the_list = self.frame.stack[-count]
        the_list.append(val)

    # 跳转
    def byte_JUMP_FORWARD(self, jump):
        self.jump(jump)

    def byte_JUMP_ABSOLUTE(self, jump):
        self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self,jump):  # 进行布尔判断，跳转到指定索引处
        val = self.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):  # 进行布尔判断，跳转到指定索引处
        val = self.pop()
        if not val:
            self.jump(jump)

    # 块
    def byte_SETUP_LOOP(self, dest):  # 设定循环块，接受目的索引为参数（handler=dest）
        self.push_block('loop', dest)

    def byte_GET_ITER(self):  # 设定生成迭代块
        self.push(iter(self.pop()))  # 弹出数据栈顶对象，生成迭代器压入数据栈顶

    def byte_FOR_ITER(self, jump):  # 设定迭代块
        iterobj = self.top()  # 弹出数据栈顶对象
        try:
            v = next(iterobj)  # 对弹出对象进行迭代，迭代所的下一个元素压入数据栈顶
            self.push(v)
        except StopIteration:  # 捕获迭代结束异常
            self.pop()
            self.jump(jump)

    def byte_BREAK_LOOP(self):
        return 'break'

    def byte_POP_BLOCK(self):
        self.pop_block()

    # 函数
    def byte_MAKE_FUNCTION(self, argc):  # 定义函数指令对应方法
        name = self.pop()
        code = self.pop()
        defaults = self.popn(argc)
        globs = self.frame.global_names  # 函数创建处的全局命名空间
        fn = Function(name, code, globs, defaults, None, self)  # 实例化Function类生成函数对象
        self.push(fn)  # 将函数对象压入数据栈

    def byte_CALL_FUNCTION(self, arg):  # 调用函数指令对应方法
        lenKw, lenPos = divmod(arg, 256)  # 计算关键字参数和位置参数数量
        posargs = self.popn(lenPos)  # 位置参数

        func = self.pop()  # 弹出函数对象
        retval = func(*posargs)  # 调用函数得出返回值
        self.push(retval)  # 压入数据栈

    def byte_RETURN_VALUE(self):  # 定义函数返回指令对应方法
        self.return_value = self.pop()  # 从数据栈中弹出返回值
        return "return"


class Frame(object):
    """
    帧是一个属性的集合，没有定义任何方法
    这些属性包括由编译器生成的代码对象；局部、全局和内置命名空间；指向前一个帧的引用；一个数据栈；一个块栈；上一个被执行的指令
    """
    def __init__(self, code_obj, global_names, local_names, prev_frame):
        self.code_obj = code_obj  # 代码对象
        self.global_names = global_names  # 全局命名空间
        self.local_names = local_names  # 局部命名空间
        self.prev_frame = prev_frame  # 前一个帧
        self.stack = []  # 创建数据栈
        if prev_frame:  # 如果存在前一个帧，则将其内置变量引入当前帧
            self.builtin_names = prev_frame.builtin_names
        else:  # 如果不存在前一个帧，则将局部命名空间中的内置模块引入作为内置命名空间(模块类型）
            self.builtin_names = local_names['__builtins__']
            if hasattr(self.builtin_names, '__dict__'):  # 内置模块中的__dict__字典属性才是名称映射对象的命名空间
                self.builtin_names = self.builtin_names.__dict__

        self.last_instruction = 0  # 指令指针置为初始值：0
        self.block_stack = []  # 创建块栈


class Function(object):
    """
    简化了细节，主要目标是实现能够调用函数，并且在调用函数时创建新的帧并运行
    创造1个拟真的函数对象，按解释器的预期进行定义
    实例化时的参数分别为：函数名称，函数的代码对象，函数的全局命名空间，函数的默认参数，函数的闭包参数,VirtualMachine实例对象）
    """
    # 限定函数类的类属性
    __slots__ = [
        'func_code', 'func_name', 'func_defaults', 'func_globals',
        'func_locals', 'func_dict', 'func_closure',
        '__name__', '__dict__', '__doc__',
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        self._vm = vm  # VirtualMachine实例对象
        self.func_code = code  # 代码对象
        self.func_name = self.__name__ = name or code.co_name  # 函数名称
        self.func_defaults = tuple(defaults)  # 默认参数
        self.func_globals = globs  # 函数的全局命名空间
        self.func_locals = self._vm.frame.local_names  # 函数的局部命名空间
        self.__dict__ = {}  # 函数的活动命名空间
        self.func_closure = closure  # 函数的闭包参数
        self.__doc__ = code.co_consts[0] if code.co_consts else None  # 函数定义中的字面常量

        # 创建字典保存默认参数和闭包参数（如果有的话）
        kw = {
            'argdefs': self.func_defaults,
        }
        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)  # 取回通过闭包cell保存的值
        self._func = types.FunctionType(code, globs, **kw)  # 调用types库创建函数类型

    def __call__(self, *args, **kwargs):
        """当调用一个函数时，创造一个新的帧并运行"""
        callargs = inspect.getcallargs(self._func, *args, **kwargs)
        # 使用callargs创造参数与值的映射并传入新的帧
        # 使用代码对象、参数与值的映射、全局命名空间，本地命名空间（为空）作为参数创建新的帧
        frame = self._vm.make_frame(
            self.func_code, callargs, self.func_globals, {}
        )
        return self._vm.run_frames(frame)


def make_cell(value):
    """创造一个真实的python闭包"""
    fn = (lambda x: lambda: x)(value)  # 将value放到闭包中，避免被回收
    return fn.__closure__[0]
