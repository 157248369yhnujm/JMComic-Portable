/*  PLEASE CONFIGURE THOSE VALUES OR OKUMA WON'T WORK.
    Adapted for JMComic Downloader integration.
    booksURL points to our Flask API that serves config JSON files.
*/
export function homeURL() {return           "/static/vendor/okuma/"}
export function readerURL() {return         "/reader"}
export function booksURL() {return          "/api/okuma/"}
export function websiteName() {return       "JM Downloader"}
export function defaultLanguage() {return   "en"}
