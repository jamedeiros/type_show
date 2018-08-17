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


class DelayTyping(object):
	COLOR_NORMAL     = 1
	COLOR_HIGHLIGHT  = 2
	COLOR_BACKGROUND = 3
	
	def __init__(self, filename, start=1, delay=None, areas=None):
		logging.info('Creating DelayTyping object.')
		self.filename = filename
		self.delay = delay
		self.areas = list()
		self.current_line = 1
		self.lines = list()
		self.start = start
		self.adjust_start = 0

		self.areas_processes(areas)

		self.curses = MyCurses()
		self.init_curses()

	@property
	def line(self):
		return self.start - self.adjust_start
	
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

	def __calculate_adjusts(self, begin):
		adjust = 0
		for area in self.areas:
			if len(area) == 3:
				if begin > area[0]:
					adjust += 1
			else:
				if begin > area[1]:
					adjust += area[1] - area[0] + 1
		return adjust

	def __in_areas(self, line):
		for idx, area in enumerate(self.areas):
			l = len(area)

			if l == 3 and area[0] == line:
				return idx, 1

			if l == 4 and area[0] <= line <= area[1]:
				return idx, area[1] - area[0] + 1

		return -1, 0

	def __adjust_start(self, area):
		adjust = 0

		if len(area) == 3:
			adjust = 1
		else:
			adjust = area[1] - area[0]

		self.adjust_start = max((self.adjust_start - adjust), 0)

	def areas_processes(self, areas):
		logging.info('Processing areas for typing.')
		aux = list()

		self.areas = list()

		logging.info('Calculating adjusts for areas size.')
		for area in areas[::-1]:
			adjust = self.__calculate_adjusts(area[0])
			if len(area) == 1:
				if area[0] < self.start:
					self.adjust_start += 1
				self.areas.append([area[0], adjust, list()])
			else:
				if area[1] < self.start:
					self.adjust_start += area[1] - area[0] + 1
				elif area[0] < self.start:
					self.adjust_start += self.start - area[0] + 1
				self.areas.append([area[0], area[1], adjust, list()])

		self.areas = self.areas[::-1]

	def prepare_file(self):
		logging.info('Prepare file to type.')
		logging.info('Prepare file content and area\'s data.')
		area = -1
		area_size = 0
		with open(self.filename, 'r') as fd:
			for line, data in enumerate(fd.readlines(), start=1):
				if area_size > 0:
					area_size -= 1
					self.areas[area][-1].append([self.COLOR_HIGHLIGHT, data])
					continue

				area, area_size = self.__in_areas(line)
				if area >= 0:
					area_size -= 1
					self.areas[area][-1].append([self.COLOR_HIGHLIGHT, data])
				else:
					self.lines.append([self.COLOR_NORMAL, data])

	def view_content(self):
		n = self.line - 1
		max_lines = len(self.lines)
		printed = 0

		term_height = self.curses.height - 1

		while n < max_lines:
			if printed >= term_height:
				break

			self.curses.write(text=self.lines[n][1], color=self.lines[n][0])
			n += 1
			printed += 1

	def delayed_write(self, line, content):
		logging.info('Writing {:4d}: {}'.format(line, content[1][:-1]))
		locate = False
		for character in content[1]:
			if not locate:
				self.curses.write(
					text = character,
					x = line - 1,
					y = 0, 
					color = content[0], 
					with_scroll = True
				)
				locate = True
			else:
				self.curses.write(
					text = character,
					color = content[0]
				)

			if self.delay is not None:
				sleep(self.delay)

	def scroll(self, area):
		logging.info('Making scroll moviment.')

		lines_to_scroll = 0
		step = 1
		begin = area[0]
		adjust = area[-2] + 1

		if begin < self.line:
			step = -1
			lines_to_scroll = max((self.line - begin + adjust), 0)
		elif begin > self.line:
			lines_to_scroll = self.start - (begin + adjust)

		logging.debug('Begin = {}, adjust = {}, start = {}, adjust_start = {}, scroll = {}'.format(begin, adjust, self.start, self.adjust_start, lines_to_scroll))

		for x in range(abs(lines_to_scroll)):
			self.start += step
			self.curses.clear()
			self.curses.write_count(initial=self.line)
			self.view_content()

			if self.delay is not None:
				sleep(0.1)

		return lines_to_scroll

	def view_file(self):
		logging.info('View a file.')
		self.curses.write_count(initial=self.line)
		self.view_content()

		height = self.curses.height

		for area in self.areas:
			if len(area) == 3:
				logging.info('Processing area {}'.format(area[0]))
			else:
				logging.info('Processing area {}-{}'.format(area[0], area[1]))
			self.curses.pause()

			begin = area[0]
			end = len(area) == 3 and begin or area[1]
			adjust = area[-2]
			content = area[-1]

			scrolled = self.scroll(area)
			self.curses.pause()

			for line in content:
				x = begin - self.line - adjust + 1
				self.delayed_write(x, line)
				begin += 1

			logging.debug('Begin = {}, scrolled = {}, Start = {}, Line = {}'.format(begin, scrolled, self.start, self.line))
			logging.debug(self.lines[self.line])
			logging.debug(self.lines[self.line - 1])
			self.lines = self.lines[:self.line] + content + self.lines[self.line:]
			self.start -= end - begin  + adjust + 2

			self.__adjust_start(area)

		curses.beep()

	def show(self):
		try:
			self.prepare_file()
			self.view_file()
			self.curses.pause()
		except Exception as e:
			logging.error(e)
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


