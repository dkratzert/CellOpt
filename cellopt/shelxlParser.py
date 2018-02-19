import numpy as np


class SymmetryElement(object):
    """
    Class representing a symmetry operation.
    """
    symm_ID = 1


    def __init__(self, symms, centric=False):
        """
        Constructor.
        """
        self.symms = symms
        self.ID = SymmetryElement.symm_ID
        SymmetryElement.symm_ID += 1
        lines = []
        trans = []
        for symm in self.symms:
            line, t = self._parse_line(symm)
            lines.append(line)
            trans.append(t)
        self.matrix = np.matrix(lines).transpose()
        self.trans = np.array(trans)
        if centric:
            self.matrix *= -1
            self.trans *= -1

    def __str__(self):
        string = '''|{aa:2} {ab:2} {ac:2}|   |{v:2}|
|{ba:2} {bb:2} {bc:2}| + |{vv:2}|
|{ca:2} {cb:2} {cc:2}|   |{vvv:2}|'''.format(aa=self.matrix[0, 0],
                                             ab=self.matrix[0, 1],
                                             ac=self.matrix[0, 2],
                                             ba=self.matrix[1, 0],
                                             bb=self.matrix[1, 1],
                                             bc=self.matrix[1, 2],
                                             ca=self.matrix[2, 0],
                                             cb=self.matrix[2, 1],
                                             cc=self.matrix[2, 2],
                                             v=self.trans[0],
                                             vv=self.trans[1],
                                             vvv=self.trans[2])
        return string

    def applyLattSymm(self, lattSymm):
        """
        Copies SymmetryElement instance and returns the copy after applying the translational part of 'lattSymm'.
        :param lattSymm: SymmetryElement.
        :return: SymmetryElement.
        """
        # newSymm = deepcopy(self)
        newSymm = SymmetryElement(self.toShelxl().split(','))
        newSymm.trans = [(self.trans[0] + lattSymm.trans[0])/1,
                            (self.trans[1] + lattSymm.trans[1])/1,
                            (self.trans[2] + lattSymm.trans[2])/1]
        return newSymm


    def toShelxl(self):
        """
        Generate and return string representation of Symmetry Operation in Shelxl syntax.
        :return: string.
        """
        axes = ['X', 'Y', 'Z']
        lines = []
        for i in range(3):
            op = self.matrix[i,]
            text = str(self.trans[i]) if self.trans[i] else ''
            for j in range(3):
                s = '' if not self.matrix[i, j] else axes[j]
                if self.matrix[i, j] < 0:
                    s = '-'+s
                elif s:
                    s = '+' + s
                text += s
            lines.append(text)
        return ', '.join(lines)

    def _parse_line(self, symm):
        symm = symm.lower().replace(' ', '')
        chars = ['x', 'y', 'z']
        line = []
        for char in chars:
            element, symm = self._partition(symm, char)
            line.append(element)
        if symm:
            trans = self._float(symm)
        else:
            trans = 0
        return line, trans

    def _float(self, string):
        try:
            return float(string)
        except ValueError:
            if '/' in string:
                string = string.replace('/', './') + '.'
                return eval('{}'.format(string))

    def _partition(self, symm, char):
        parts = symm.partition(char)
        if parts[1]:
            if parts[0]:
                sign = parts[0][-1]
            else:
                sign = '+'
            if sign is '-':
                return -1, ''.join((parts[0][:-1], parts[2]))
            else:
                return 1, ''.join((parts[0], parts[2])).replace('+', '')
        else:
            return 0, symm

class ShelxlLine(object):
    def __init__(self, line):
        self.line = line
        # print(self.line)

    def __str__(self):
        return 'LINE: ' + self.line


class ShelxlAtom(object):
    def __init__(self, line):
        data = [word for word in line.split() if word]
        data = [float(word) if i else word for i, word in enumerate(data)]
        self.data = data
        self.name = data[0]
        self.sfac = data[1]
        self.frac = np.array(data[2:5])
        self.occ = (data[5] // 1, data[5] % 1)
        self.adp = np.array(data[6:])
        if self.name[0].upper() == 'Q':
            self.qPeak = True
            ShelxlParser.CURRENTMOLECULE.addQPeak(self)
        else:
            self.qPeak = False
            ShelxlParser.CURRENTMOLECULE.addAtom(self)

    def __str__(self):
        return 'ATOM: ' + str(self.data)


class ShelxlMolecule(object):
    def __init__(self):
        self.sfacs = []
        self.customSfacData = {}
        self.atoms = []
        self.qPeaks = []
        self.cell = []
        self.cerr = []
        self.lattOps = []
        self.symms = []
        self.centric = False
        self.eqivs = {}
        self.dfixs = []
        self.dfixErr = 0.02

    def distance(self, atom1, atom2):
        x, y, z = atom1.frac
        try:
            xx, yy, zz = atom2.frac + 99.5
        except TypeError:
            xx, yy, zz = np.array(atom2.frac) + 99.5
        dx = (xx - x) % 1 - 0.5
        dy = (yy - y) % 1 - 0.5
        dz = (zz - z) % 1 - 0.5
        a, b, c, alpha, beta, gamma = self.cell
        alpha = alpha / 180. * np.pi
        beta = beta / 180. * np.pi
        gamma = gamma / 180. * np.pi
        dd = a ** 2 * dx ** 2 + b ** 2 * dy ** 2 + c ** 2 * dz ** 2 + 2 * b * c * np.cos(
            alpha) * dy * dz + 2 * a * c * np.cos(beta) * dx * dz + 2 * a * b * np.cos(gamma) * dx * dy
        return dd ** .5

    def addAtom(self, atom):
        self.atoms.append(atom)

    def addQPeak(self, qPeak):
        self.qPeaks.append(qPeak)

    def setCell(self, cell):
        self.cell = np.array([float(c) for c in cell])

    def setWavelength(self, w):
        self.waveLength = float(w)

    def setZ(self, z):
        self.z = int(z)

    def setCerr(self, cerr):
        self.cerr = np.array([float(c) for c in cerr])

    def addSfac(self, sfac):
        self.sfacs.append(sfac)

    def addCustomSfac(self, data):
        symbol = data[0]
        data = [float(datum) for datum in data[1:]]
        data = [symbol] + data
        self.customSfacData[symbol] = data
        self.sfacs.append(symbol)

    def addSymm(self, symmData):
        newSymm = SymmetryElement(symmData)
        self.symms.append(newSymm)
        for symm in self.lattOps:
            lattSymm = newSymm.applyLattSymm(symm)
            self.symms.append(lattSymm)
        if self.centric:
            self.symms.append(SymmetryElement(symmData, centric=True))
            for symm in self.lattOps:
                lattSymm = newSymm.applyLattSymm(symm)
                self.symms.append(lattSymm)

    def setCentric(self, value):
        self.centric = value

    def setLattOps(self, lattOps):
        self.lattOps = lattOps

    def addDfix(self, value, err, targets):
        self.dfixs.append((value, err, targets))

    def addEqiv(self, name, data):
        symm = SymmetryElement(data)
        self.eqivs[name] = symm


    def finalize(self):
        # self._finalizeEqiv()
        # return
        self._finalizeDfix()


    def _finalizeEqiv(self):
        for name, eqiv in self.eqivs.items():
            newFrac = np.dot(atom.frac, symm.matrix) + symm.trans
            print(name, eqiv)

    def _finalizeDfix(self):
        dfixTable = {atom.name.upper(): {} for atom in self.atoms}
        # for atom in self.atoms:
        #     print(atom.name)
        for target, err, pairs in self.dfixs:
            if not err:
                err = self.dfixErr
            for atom1, atom2 in pairs:
                atom1 = atom1.upper()
                try:
                    tableRow1 = dfixTable[atom1]
                except KeyError:
                    tableRow1 = {}
                    dfixTable[atom1] = tableRow1
                try:
                    tableField1 = tableRow1[atom2]
                except KeyError:
                    tableRow1[atom2] = (target, err)
                # else:
                #     tableField1.append((target, err))

                atom2 = atom2.upper()
                try:
                    tableRow2 = dfixTable[atom2]
                except KeyError:
                    tableRow2 = {}
                    dfixTable[atom2] = tableRow2
                try:
                    tableField2 = tableRow2[atom1]
                except KeyError:
                    tableRow2[atom1] = (target, err)
                # else:
                #     tableField2.append((target, err))
        for k, v in dfixTable.items():
            print(k, v)

class ShelxlParser(object):
    CURRENTMOLECULE = None

    def __init__(self):
        self.lines = []
        self.atoms = []

    def read(self, fileName):
        ShelxlParser.CURRENTMOLECULE = ShelxlMolecule()
        parser = LineParser()
        with Reader(fileName) as reader:
            for line in reader.readlines():
                if line[0] is '+':
                    reader.insert(line[1:-1])
                    line = '+    ' + line[1:]
                parser, line = parser(line)
                if line:
                    self.lines.append(line)
        # for line in self.lines:
        #     print(line)

        # for atom1 in self.CURRENTMOLECULE.atoms:
            # for atom2 in self.CURRENTMOLECULE.atoms:
            #     print(self.CURRENTMOLECULE.distance( atom1, atom2))
            # print(atom1.name)
        molecule = ShelxlParser.CURRENTMOLECULE
        molecule.finalize()
        ShelxlParser.CURRENTMOLECULE = None


class BaseParser(object):
    RETURNTYPE = None

    def __init__(self, line):
        self.body = line

    def __call__(self, line):
        self.finished()
        return LineParser(), line

    def get(self, previousParser):
        if not self.body.endswith('='):
            self.finished()
            return previousParser, self.RETURNTYPE(self.body)
        else:
            self.body = self.body[:-1]
            return self, None

    def finished(self):
        pass


class LineParser(BaseParser):
    def __init__(self):
        self.COMMANDS = {'REM': self.doNothing,
                         'BEDE': self.doNothing,
                         'MOLE': self.doNothing,
                         'TITL': self.doNothing,
                         'CELL': CellParser,
                         'ZERR': CerrParser,
                         'LATT': self.doNothing,
                         'SYMM': SymmParser,
                         'SFAC': SfacParser,
                         'UNIT': self.doNothing,
                         'TEMP': self.doNothing,
                         'L.S.': self.doNothing,
                         'BOND': self.doNothing,
                         'ACTA': self.doNothing,
                         'LIST': self.doNothing,
                         'FMAP': self.doNothing,
                         'PLAN': self.doNothing,
                         'WGHT': self.doNothing,
                         'FVAR': self.doNothing,
                         'SIMU': self.doNothing,
                         'RIGU': self.doNothing,
                         'SADI': self.doNothing,
                         'SAME': self.doNothing,
                         'DANG': self.doNothing,
                         'AFIX': self.doNothing,
                         'PART': self.doNothing,
                         'HKLF': self.doNothing,
                         'ABIN': self.doNothing,
                         'ANIS': self.doNothing,
                         'ANSC': self.doNothing,
                         'ANSR': self.doNothing,
                         'BASF': self.doNothing,
                         'BIND': self.doNothing,
                         'BLOC': self.doNothing,
                         'BUMP': self.doNothing,
                         'CGLS': self.doNothing,
                         'CHIV': self.doNothing,
                         'CONF': self.doNothing,
                         'CONN': self.doNothing,
                         'DAMP': self.doNothing,
                         'DEFS': self.doNothing,
                         'DELU': self.doNothing,
                         'DFIX': DfixParser,
                         'DISP': self.doNothing,
                         'EADP': self.doNothing,
                         'EQIV': EqivParser,
                         'EXTI': self.doNothing,
                         'EXYZ': self.doNothing,
                         'FEND': self.doNothing,
                         'FLAT': self.doNothing,
                         'FMAP': self.doNothing,
                         'FRAG': self.doNothing,
                         'FREE': self.doNothing,
                         'GRID': self.doNothing,
                         'HFIX': self.doNothing,
                         'HTAB': self.doNothing,
                         'ISOR': self.doNothing,
                         'LATT': LattParser,
                         'LAUE': self.doNothing,
                         'MERG': self.doNothing,
                         'MORE': self.doNothing,
                         'MPLA': self.doNothing,
                         'NCSY': self.doNothing,
                         'NEUT': self.doNothing,
                         'OMIT': self.doNothing,
                         'PLAN': self.doNothing,
                         'PRIG': self.doNothing,
                         'RESI': self.doNothing,
                         'RTAB': self.doNothing,
                         'SADI': self.doNothing,
                         'SAME': self.doNothing,
                         'SHEL': self.doNothing,
                         'SIMU': self.doNothing,
                         'SIZE': self.doNothing,
                         'SPEC': self.doNothing,
                         'STIR': self.doNothing,
                         'SUMP': self.doNothing,
                         'SWAT': self.doNothing,
                         'TWIN': self.doNothing,
                         'TWST': self.doNothing,
                         'WIGL': self.doNothing,
                         'WPDB': self.doNothing,
                         'XNPD': self.doNothing,
                         'REM': self.doNothing,
                         'Q': self.doNothing,
                         'END': self.doNothing,
                         'BEDE': self.doNothing,
                         'LONE': self.doNothing,
                         '+': self.doNothing,
                         }

    def __call__(self, line):
        line = line.rstrip('\n')
        if not line:
            return self.doNothing(line)
        command = line[:4]
        if command[0] is ' ':
            action = self.doNothing
        else:
            try:
                action = self.COMMANDS[command.rstrip()]
                if isinstance(action, type):
                    parser = action(line)
                    return parser.get(self)
            except KeyError:
                atomParser = AtomParser(line)
                return atomParser.get(self)
        return action(line)

    def doNothing(self, line):
        return self, ShelxlLine(line)


class AtomParser(BaseParser):
    RETURNTYPE = ShelxlAtom

    def __call__(self, line):
        return LineParser(), ShelxlAtom(self.body + line)


class CellParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        data = np.array([float(word) for word in self.body.split()[1:] if word])
        ShelxlParser.CURRENTMOLECULE.setCell(data[1:])
        ShelxlParser.CURRENTMOLECULE.setWavelength(data[0])


class CerrParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        data = np.array([float(word) for word in self.body.split()[1:] if word])
        ShelxlParser.CURRENTMOLECULE.setCerr(data[1:])
        ShelxlParser.CURRENTMOLECULE.setZ(data[0])


class SfacParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        custom = False
        words = [word for word in self.body.split()[1:] if word]
        for word in words:
            try:
                word = float(word)
            except ValueError:
                pass
            else:
                custom = True
                break
        if not custom:
            for sfac in words:
                ShelxlParser.CURRENTMOLECULE.addSfac(sfac)
        else:
            ShelxlParser.CURRENTMOLECULE.addCustomSfac(words)


class LattParser(BaseParser):
    LATTDICT = {1: [],
                2: [SymmetryElement(('.5', '.5', '.5'))],
                3: [],
                4: [SymmetryElement(('.5', '.5', '0')),
                    SymmetryElement(('.5', '0', '.5')),
                    SymmetryElement(('0', '.5', '.5'))],
                5: [SymmetryElement(('0', '.5', '.5'))],
                6: [SymmetryElement(('.5', '0', '.5'))],
                7: [SymmetryElement(('.5', '.5', '0'))],
                }
    RETURNTYPE = ShelxlLine

    def finished(self):
        data = [word for word in self.body.split() if word]
        latt = int(data[-1])
        if latt > 0:
            ShelxlParser.CURRENTMOLECULE.setCentric(True)
        lattOps = LattParser.LATTDICT[abs(latt)]
        ShelxlParser.CURRENTMOLECULE.setLattOps(lattOps)


class SymmParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        symmData = self.body[4:].split(',')
        ShelxlParser.CURRENTMOLECULE.addSymm(symmData)


class DfixParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        data = [word for word in self.body[4:].split() if word]
        value, data = float(data[0]), data[1:]
        try:
            err = float(data[0])
        except ValueError:
            err = None
        else:
            data = data[1:]
        pairs = []
        for i in range(len(data)//2):
            i, j = 2*i, 2*i+1
            pairs.append((data[i], data[j]))
            ShelxlParser.CURRENTMOLECULE.addDfix(value, err, pairs)


class EqivParser(BaseParser):
    RETURNTYPE = ShelxlLine

    def finished(self):
        data = [word for word in self.body.split() if word][1:]
        name = data.pop(0)
        data = ' '.join(data)
        data = data.split(',')
        ShelxlParser.CURRENTMOLECULE.addEqiv(name, data)


class Reader(object):
    """
    Super awesome class for reading files that might contain references to other files and you don't want to deal
    with that hassle.

    If file a.txt is:
        1
        2
        3
    and file b.txt is:
        a
        b
        c
    the code
        with Reader('a.txt') as reader:
            for line in reader.readlines():
                    if '2' in line:
                            reader.insert('b.txt')
                    if 'b' in line:
                            reader.remove()
                    print line
    will print
        1
        2
        a
        b
        3
    """

    def __init__(self, fileName):
        self.fileName = fileName
        self.inserted = None
        self.open = False
        self.fp = None

    def readlines(self, ):
        """
        Provides an interface equivalent to filePointer.readlines().
        :return: Yield string.
        """
        if not self.open:
            self.fp = open(self.fileName, 'r')
        while True:
            n = None
            if self.inserted:
                n = self.inserted.readline()
            if not n:
                n = self.fp.readline()
            if not n:
                raise StopIteration
            yield n

    def __exit__(self, *args):
        self.fp.close()
        try:
            self.inserted.close()
        except AttributeError:
            pass

    def __enter__(self):
        self.fp = open(self.fileName, 'r')
        return self

    def insert(self, fileName):
        """
        Insert a second file with a given name. After this method is called, each consecutive call to 'readlines' will
        yield a line of the inserted file until the inserted file yields EOF or 'remove' is called.
        :param fileName: string.
        :return: None
        """
        try:
            self.inserted = open(fileName, 'r')
        except FileNotFoundError:
            print('Cannot find insertion file.')

    def remove(self):
        """
        Removes a previously inserted file to stop yielding from the inserted file and continuing with the base file.
        :return:
        """
        self.inserted.close()
        self.inserted = None

    def fileInserted(self):
        """
        Check whether 'readlines' is currently yielding lines from an inserted file, or the base file.
        :return: bool.
        """
        return True if self.inserted else False


if __name__ == '__main__':
    ShelxlParser().read('s1.ins')
