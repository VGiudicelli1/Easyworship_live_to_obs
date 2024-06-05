

class Slide:
    id: int
    rowid: int
    revision: int
    infoRecived: bool
    infoRequested: bool
    content: str
    title: str
    NULL: "Slide"

    def __init__(self: "Slide", id: int, rowid: int, revision: int):
        self.id = id
        self.rowid = rowid
        self.revision = revision
        self.infoRecived = False
        self.infoRequested = False
        self.content = ''
        self.title = ''

    def reciveInfo(self: "Slide", content: str, title: str):
        self.content = content
        self.title = title
        self.infoRecived = True

    def requestInfo(self: "Slide"):
        self.infoRequested = True

    def __str__(self: "Slide") -> str:
        if not self.isNull():
            return "Slide NULL"
        return "Slide [row_id: {rowid}, title: {title}, content: {content}]".format(rowid = self.rowid, title = self.title, content = self.content)
    
    def isNull(self: "Slide") -> bool:
        return self.rowid >= 0
    
    def __bool__(self: "Slide") -> bool:
        return self.isNull()

Slide.NULL = Slide(-1, -1, -1)

class Storage:
    content_sent: None
    contentvisible: bool
    contentvisible_pending: bool
    credit: None
    credit_sent: None
    imagehash: None
    imagehash_pending: bin
    liverev: int
    liverev_pending: int
    pres_rowid: int
    presentation_filtered: bool
    requestrev: int
    slide_rowid_pending: int
    slides: "dict[int, Slide]"

    def __init__(self: "Storage"):
        self.slide_rowid_pending = -1
        self.requestrev = 0
        self.liverev_pending = -1
        self.imagehash_pending = ''
        self.contentvisible_pending = False
        self.contentvisible = True
        self.presentation_filtered = True

        self.imagehash = ''

        self.liverev = 0
        self.pres_rowid = 0

        self.clearSlides()

    def getSlide(self: "Storage", row_id: int) -> Slide:
        slide = self.slides.get(row_id)
        if (slide):
            return slide
        return Slide.NULL

    def setSlide(self: "Storage", slide: Slide) -> bool:
        if (slide.rowid in self.slides):
            return False
        self.slides[slide.rowid] = slide
        return True
    
    def getCurrentSlide(self: "Storage") -> Slide:
        return self.getSlide(self.slide_rowid_pending)
    
    def clearSlides(self: "Storage") -> None:
        self.credit = ''
        self.presentation_filtered = True
        self.slides = {}
        self.title = ''

    def hasSlide(self: "Storage", row_id: int) -> bool:
        return row_id in self.slides
    
    def getAllSlides(self: "Storage") -> "list[Slide]":
        return list(self.slides.values())


if __name__ == '__main__':
    store = Storage()

    s = Slide(0, 1, 2)
    s.reciveInfo('coucou', 'titre')

    print('add slide: ', store.setSlide(s))

    print('get slide: ', store.getSlide(1))
    print('get slide: ', store.getSlide(2))

    pass