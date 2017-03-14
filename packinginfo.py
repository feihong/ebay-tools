import attr


@attr.s
class OutputMeta:
    """
    This class stores the output parameters for a particular type of shipping
    label output.

    """
    entries = {}

    type = attr.ib(default='')      # type of tracking number
    translate = attr.ib(default=(10, 10))
    rotate = attr.ib(default=0)
    max_len = attr.ib(default=20)
    max_lines = attr.ib(default=2)

    @classmethod
    def add_meta(cls, type, **kwargs):
        cls.entries[type] = OutputMeta(type=type, **kwargs)

    @classmethod
    def get(cls, type):
        return cls.entries[type]

    @staticmethod
    def get_output_info(type, text):
        meta = OutputMeta.get(type)
        if meta.max_len is not None:
            text = textwrap.fill(text, meta.max_len)

        if meta.max_lines is not None:
            overflow = len(text.splitlines()) > meta.max_lines
        else:
            overflow = False

        return OutputInfo(
            text=text,
            overflow=overflow,
            translate=meta.translate,
            rotate=meta.rotate,
        )


OutputMeta.add_meta(
    type='bulk-domestic-top',
    translate=(244, 316),
    rotate=0,
    max_len=27,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-domestic-bottom',
    translate=(244, 713),
    rotate=0,
    max_len=27,
    max_lines=2,
)
OutputMeta.add_meta(
    type='bulk-domestic-center-line',
    translate=(45, 397),
    rotate=0,
    max_len=None,
    max_lines=None,
)
OutputMeta.add_meta(
    type='bulk-foreign',
    translate=(537, 143),
    rotate=-90,
    max_len=21,
    max_lines=5,
)
OutputMeta.add_meta(
    type='single-domestic',
    translate=(223, 318),
    rotate=0,
    max_len=28,
    max_lines=2,
)
OutputMeta.add_meta(
    type='username',
    translate=(45, 767),
    rotate=0,
    max_len=50,
    max_lines=1,
)
OutputMeta.add_meta(
    type='page-number',
    translate=(430, 767),
    rotate=0,
    max_len=30,
    max_lines=1,
)


@attr.s(repr=False)
class OutputInfo:
    text = attr.ib(default='xxx xxx')
    overflow = attr.ib(default=False)       # if text takes up too many lines
    translate = attr.ib(default=(10, 10))
    rotate = attr.ib(default=0)

    def __repr__(self):
        return '{} {}'.format(self.text, self.translate)


def get_center_line():
    return OutputMeta.get_output_info('domestic-center-line', '-  ' * 30)


def get_page_number(num, total, label_count):
    return OutputMeta.get_output_info(
        'page-number',
        'Page {} of {} ({} labels)'.format(num, total, label_count))


def get_username(text):
    return OutputMeta.get_output_info('username', 'User: {}'.format(text))
