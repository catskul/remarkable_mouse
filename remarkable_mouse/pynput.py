import logging
import struct
import select
import libevdev


stylus_width = 15725
stylus_height = 20951

class FakeLocalDevice:

    def __init__(self, args):
        from screeninfo import get_monitors
        from pynput.mouse import Button, Controller

        
        self.lifted = True
        self.new_x = self.new_y = False
        self.mouse = Controller()
        self.threshold = args.threshold

        self.monitor = get_monitors()[args.monitor]
        
        logging.basicConfig(format='%(message)s')

        self.log = logging.getLogger(__name__)
        self.log.debug('Chose monitor: {}'.format(self.monitor))

    def fit(x, y, stylus_width, stylus_height, monitor, orientation):

        if orientation == 'vertical':
            y = stylus_height - y
        elif orientation == 'right':
            x, y = y, x
            stylus_width, stylus_height = stylus_height, stylus_width
        elif orientation == 'left':
            x, y = stylus_height - y, stylus_width - x
            stylus_width, stylus_height = stylus_height, stylus_width

        ratio_width, ratio_height = monitor.width / stylus_width, monitor.height / stylus_height
        scaling = ratio_width if ratio_width > ratio_height else ratio_height

        return (
            scaling * (x - (stylus_width - monitor.width / scaling) / 2),
            scaling * (y - (stylus_height - monitor.height / scaling) / 2)
        )


    def send_events(self, events):
        from pynput.mouse import Button

        for event in events:
            print(dir(event))
            print(event.type)
            if event.type == libevdev.EV_ABS:

                # handle x direction
                if event.code == libevdev.EV_ABS.ABS_X:
                    self.log.debug(event.value)
                    x = event.value
                    self.new_x = True

                # handle y direction
                elif event.code == libevdev.EV_ABS.ABS_X:
                    self.log.debug('\t{}'.format(event.value))
                    y = event.value
                    self.new_y = True

                # handle draw
                elif event.code == libevdev.EV_ABS.ABS_PRESSURE:
                    self.log.debug('\t\t{}'.format(event.value))
                    if event.value > self.threshold:
                        if self.lifted:
                            self.log.debug('PRESS')
                            self.lifted = False
                            self.mouse.press(Button.left)
                    else:
                        if not self.lifted:
                            self.log.debug('RELEASE')
                            self.lifted = True
                            self.mouse.release(Button.left)
                else:
                    self.log.debug('\t\tunhandled code: {} : {}'.format(event.code, event.value))


                # only move when x and y are updated for smoother mouse
                if self.new_x and self.new_y:
                    mapped_x, mapped_y = self.fit(x, y, stylus_width, stylus_height, self.monitor, args.orientation)
                    self.mouse.move(
                        self.monitor.x + mapped_x - self.mouse.position[0],
                        self.monitor.y + mapped_y - self.mouse.position[1]
                    )
                    self.new_x = self.new_y = False
            elif event.type == libevdev.EV_KEY:
                self.log.debug('\t\tunhandled button event: {} : {}'.format(event.code, event.value))
            elif event.type == libevdev.EV_SYN:
                self.log.debug('\t\tunhandled sync event: {} : {}'.format(event.code, event.value))
            else:
                self.log.debug('\t\tunhandled event: {} : {} : {}'.format(event.type, event.code, event.value))
