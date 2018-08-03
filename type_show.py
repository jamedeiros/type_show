import argparse
import curses
import sys
from time import sleep


class MyCurses(object):

	def __init__(self):
		self.initialized_color = False
		self.mainwin = curses.initscr()
		self.height, self.width = self.mainwin.getmaxyx()
		self.height -= 1

		count_width = 4

		self.count_win = curses.newwin(self.height, count_width, 0, 0)
		self.data_win = curses.newwin(self.height, self.width - count_width, 0, 3)

	#B:TYPE - 1#
	def write_count(self, initial=1):
		for i in range(self.height):
			self.count_win.addstr(i, 0, '{:2d}'.format(initial + i))
		self.count_win.refresh()
	#E:TYPE#

	def set_color_pair(self, idx, foreground, background):
		if not self.initialized_color:
			curses.start_color()
		curses.init_pair(idx, foreground, background)

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
	COLOR_NORMAL    = 1
	COLOR_HIGHLIGHT = 2
	
	def __init__(self, filename, delay=None, begin=None, end=None):
		self.filename = filename
		self.delay = delay
		self.begin = begin
		self.end = end

		self.curses = MyCurses()
		self.curses.set_color_pair(
			idx = self.COLOR_NORMAL, 
			foreground = curses.COLOR_WHITE, 
			background = curses.COLOR_BLACK
			)
		self.curses.set_color_pair(
			idx = self.COLOR_HIGHLIGHT,
			foreground = curses.COLOR_BLACK,
			background = curses.COLOR_CYAN
		)

	def delayed_write(self, line, n):
		locate = False
		if len(line) == 0:
				self.curses.write(
					text = '',
					x = n,
					y = 0, 
					color = self.COLOR_HIGHLIGHT, 
					with_scroll = True
				)

				if self.delay is not None:
					sleep(self.delay)
		else:
			for character in line:
				if not locate:
					self.curses.write(
						text = character,
						x = n,
						y = 0, 
						color = self.COLOR_HIGHLIGHT, 
						with_scroll = True
					)
					locate = True
				else:
					self.curses.write(
						text = character,
						color = self.COLOR_HIGHLIGHT
					)

				if self.delay is not None:
					sleep(self.delay)

	def view_fixed_content(self, lines):
		printed = 0

		for n, line in enumerate(lines, 1):
			if printed >= self.curses.height - 1:
				break

			if self.begin <= n <= self.end:
				continue

			printed += 1
			self.curses.write(text=line, color=self.COLOR_NORMAL)

	def view_file(self):
		lines = None

		with open(self.filename, 'r') as fd:
			lines = fd.readlines()

		self.curses.write_count()
		self.view_fixed_content(lines)
		self.curses.pause()

		for n in range(self.begin - 1, self.end):
			self.delayed_write(lines[n][:-1], n)

	def show(self):
		try:
			self.view_file()
			self.curses.pause()
		except:
			pass
		finally: 
			self.curses.finalize()


def run():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help="filename for view")
	parser.add_argument("--delay", help="typing delay when showing", type=float)
	parser.add_argument("--begin", help="begin for typing", type=int)
	parser.add_argument("--end", help="end for typing", type=int)
	args = parser.parse_args()

	filename = args.filename
	delay = None
	begin = None
	end = None

	if args.delay:
		delay = args.delay

	if args.begin:
		begin = args.begin

	if args.end:
		end = args.end

	obj = DelayTyping(filename, delay=delay, begin=begin, end=end)
	obj.show()


if __name__ == '__main__':
	run()


