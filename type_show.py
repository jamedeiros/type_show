import argparse
import curses
import logging
import sys

from time import sleep

log_filename = 'typing.log'
logging.basicConfig(filename=log_filename, format='[%(levelname)s]: %(message)s', level=logging.DEBUG)
logging.info('-' * 80)


class MyCurses(object):

	def __init__(self):
		self.initialized_color = False
		self.mainwin = curses.initscr()
		self.height, self.width = self.mainwin.getmaxyx()
		self.height -= 1

		self.count_width = 4

	def init_windows(self, background):
		self.count_win = curses.newwin(self.height, self.count_width, 0, 0)
		self.count_win.bkgd(' ', curses.color_pair(background))

		self.data_win = curses.newwin(self.height, self.width - self.count_width, 0, 3)
		self.data_win.bkgd(' ', curses.color_pair(background))

	def write_count(self, initial=1):
		self.count_win.clear()
		for i in range(self.height):
			self.count_win.addstr(i, 0, '{:2d}'.format(initial + i))
		self.count_win.refresh()

	def set_color_pair(self, idx, foreground, background):
		if not self.initialized_color:
			curses.start_color()
		curses.init_pair(idx, foreground, background)

	def clear(self):
		self.data_win.clear()

	def move(self, x, y):
		self.data_win.move(x, y)

	def write(self, text, x=None, y=None, color=None, with_scroll=False):
		if x is not None:
			self.move(x, y)

		if with_scroll:
			self.data_win.insertln()

		if color is not None:
			self.data_win.addstr(text, curses.color_pair(color))
		else:
			self.data_win.addstr(text)
		self.data_win.refresh()

	def pause(self):
		self.data_win.getch()

	def finalize(self):
		curses.endwin()


class FileLine(object):
	LINE_NORMAL    = 1
	LINE_HIGHLIGHT = 2

	def __init__(self, data, property=LINE_NORMAL):
		self.data = data
		self.property = property
		self.hided = False

	def __str__(self):
		return '{}[{}] {}'.format(self.hided and '-' or '+', self.get_property(), self.data)

	def get_property(self):
		if self.property == FileLine.LINE_HIGHLIGHT:
			return 'Highlight'
		return 'Normal'


class HideArea(object):

	def __init__(self, begin, end=None):
		self.processed = False
		self.begin = begin
		self.end = end
		self.content = list()

	def __str__(self):
		return 'Begin = {}; End = {}'.format(self.begin, self.end)

	@property
	def size(self):
		size = self.end - self.begin + 1
		if self.begin == self.end:
			size = 1
		return size


class FileData(object):

	def __init__(self, lines):
		self.lenght = 0
		self.content = list()
		self.hided = list()

		for line in lines:
			self.lenght += 1
			self.content.append(FileLine(data=line))

	def __getattr__(self, method):	
		return getattr(self.content, method)

	def __len__(self):
		return len(self.content)

	def __getitem__(self, key):
		return self.content[key]

	def add_hide_area(self, begin, end=None):
		if end is None:
			end = begin

		for x in range(begin -1, end):
			self.content[x].hided = True
			self.content[x].property = FileLine.LINE_HIGHLIGHT

		hided_area = HideArea(begin=begin, end=end)
		hided_area.content = self.content[begin - 1: end]

		self.hided.append(hided_area)

	def hide_areas(self):
		for x in range(len(self.content)-1, -1, -1):
			if self.content[x].hided:
				del self.content[x]

	def get_hided_data(self, area):
		lines = list()
		for x  in range(area.begin - 1, area.end):
			lines.append(self.content[x])
		return lines

	def proccess_hided_area(self, area):
		adjust = self.calculate_adjust(area.begin)
		self.content = self.content[:area.begin-adjust] + area.content + self.content[area.begin-adjust:]
		area.processed = True

	def calculate_adjust(self, value):
		adjust = 0
		for area in self.hided:
			if not area.processed:
				if area.end <= value:
					adjust += area.size
				elif area.begin <= value:
					adjust += value - area.begin
				logging.debug('************* Value = {}, Begin = {}, End = {}, Adjust = {}'.format(value, area.begin, area.end, adjust))
		return adjust + 1
		

class DelayTyping(object):
	COLOR_NORMAL     = 1
	COLOR_HIGHLIGHT  = 2
	COLOR_BACKGROUND = 3
	
	def __init__(self, filename, start=1, delay=None, areas=None):
		logging.info('Creating DelayTyping object.')
		self.filename = filename
		self.delay = delay
		self.file_data = None
		self.line = start

		with open(self.filename, 'r') as fd:
			self.file_data = FileData(lines=fd.readlines())

		for area in areas:
			if len(area) == 1:
				self.file_data.add_hide_area(begin=area[0], end=area[0])
			else:
				self.file_data.add_hide_area(begin=area[0], end=area[1])

		self.file_data.hide_areas()

		self.curses = MyCurses()
		self.init_curses()

	def __get_color(self, type):
		color = DelayTyping.COLOR_NORMAL
		if type == FileLine.LINE_HIGHLIGHT:
			color = DelayTyping.COLOR_HIGHLIGHT
		return color

	def init_curses(self):
		logging.info('Initializing curses enviroment.')
		self.curses.set_color_pair(
			idx = self.COLOR_NORMAL, 
			foreground = curses.COLOR_BLACK, 
			background = curses.COLOR_WHITE
			)
		self.curses.set_color_pair(
			idx = self.COLOR_HIGHLIGHT,
			foreground = curses.COLOR_BLACK,
			background = curses.COLOR_CYAN
		)
		self.curses.set_color_pair(
			idx = self.COLOR_BACKGROUND,
			foreground = curses.COLOR_BLACK,
			background = curses.COLOR_WHITE
		)
		self.curses.init_windows(self.COLOR_BACKGROUND)

	def view_content(self):
		n = self.line - 1
		max_lines = len(self.file_data)
		printed = 0

		term_height = self.curses.height - 1

		while n < max_lines:
			if printed >= term_height:
				break
			data = self.file_data[n]
			color = data.property == FileLine.LINE_NORMAL and DelayTyping.COLOR_NORMAL or DelayTyping.COLOR_HIGHLIGHT
			self.curses.write(text=data.data, color=color)
			printed += 1
			n += 1

	def delayed_write(self, area, adjust, count, content):
		logging.info('Writing: {}'.format(content.data[:-1]))
		logging.debug('Start = {}, Begin = {}, End = {}, Size = {}, Adjust = {}, Count = {}'.format(self.line, area.begin, area.end, area.size, adjust, count))
		locate = False
		for character in content.data:
			if not locate:
				begin = area.begin - adjust - self.line + 1
				logging.debug('START = {}; BEGIN == {}'.format(self.line,  begin))

				self.curses.write(
					text = character,
					x = begin + count,
					y = 0, 
					color = self.__get_color(content.property), 
					with_scroll = True
				)
				locate = True
			else:
				self.curses.write(
					text = character,
					color = self.__get_color(content.property)
				)

			if self.delay is not None:
				sleep(self.delay)

	def scroll(self, area, adjust):
		logging.info('Making scroll moviment.')
		logging.debug('Line = {}, Height = {}, area.size = {}, area.begin = {}, adjust = {}'.format(self.line, self.curses.height, area.size, area.begin, adjust))

		step = 0
		lines_to_scroll = 0

		if self.line > area.begin:
			logging.debug('Scroll IF - {}'.format(self.line - area.begin + adjust + area.size))
			step = -1
			lines_to_scroll = self.line - area.begin + adjust
		elif (self.line + self.curses.height) < area.begin:
			logging.debug('Scroll ELIF - {}'.format(area.begin - self.line - adjust))
			step = 1
			lines_to_scroll = area.begin - self.line - adjust

		logging.debug('Step = {}, Lines to Scroll = {}'.format(step, lines_to_scroll))

		for x in range(abs(lines_to_scroll)):
			self.line += step
			self.curses.clear()
			self.curses.write_count(initial=self.line)
			self.view_content()

			if self.delay is not None:
				sleep(0.1)

	def view_file(self):
		logging.info('View a file.')
		self.curses.write_count(initial=self.line)
		self.view_content()

		height = self.curses.height

		for area in self.file_data.hided:
			logging.debug(area)
			self.curses.pause()

			adjust = self.file_data.calculate_adjust(area.begin - 1)
			scrolled = self.scroll(area=area, adjust=adjust)
			self.curses.pause()

			count_line = 0
			self.file_data.proccess_hided_area(area)
			for line in area.content:
				self.delayed_write(area=area, adjust=adjust, count=count_line, content=line)
				line.hided = False
				count_line += 1

		curses.beep()

	def show(self):
		try:
			self.view_file()
			self.curses.pause()
		except Exception as e:
			logging.exception("Traceback")
		finally: 
			self.curses.finalize()


def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help="filename for view")
	parser.add_argument("--start", help="initial line to show", type=int)	
	parser.add_argument("--delay", help="typing delay when showing", type=float)
	parser.add_argument("--areas", help="areas to type, example: 10-20")
	args = parser.parse_args()

	filename = args.filename
	delay = None
	start = 1
	areas = list()

	if args.start:
		start = args.start

	if args.delay:
		delay = args.delay

	if args.areas:
		for area in args.areas.split(','):
			data = area.split('-')
			if len(data) > 1:
				areas.append([int(data[0]), int(data[1])])
			else:
				areas.append([int(data[0])])

	logging.info('Stating with start={}, delay={}'.format(start, delay))

	obj = DelayTyping(filename, start=start, delay=delay, areas=areas)
	obj.show()


if __name__ == '__main__':
	run()


