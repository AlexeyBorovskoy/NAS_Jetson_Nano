# tg_curl_timeout.awk — используется разделом 7в scripts/quality/preflight.sh (CQ-10).
# Склеивает строки-продолжения shell, находит логические строки с curl и sendMessage
# и печатает «BAD файл:строка» для вызовов без --max-time / -m; в конце «COUNT n».
# Вынесено из preflight.sh, чтобы функцию раздела можно было читать и проверять отдельно.
BEGIN { CR = sprintf("%c", 13) }
function emit() {
    if (buf ~ /^[[:space:]]*#/) { buf = ""; ln = 0; return }
    if (buf ~ /curl/ &&
        buf ~ /sendMessage/) {
        calls++
        if (index(buf, "--max-time") == 0 &&
            buf !~ /[[:space:]]-m([[:space:]]|[0-9])/) {
            printf "BAD %s:%d\n", FILENAME, ln
        }
    }
    buf = ""
    ln = 0
}
{
    line = $0
    if (length(line) > 0 && substr(line, length(line)) == CR)
        line = substr(line, 1, length(line) - 1)
    if (buf == "") ln = NR
    if (line ~ /\\$/) {
        sub(/\\$/, "", line)
        buf = buf " " line
        next
    }
    buf = buf " " line
    emit()
}
END {
    if (buf != "") emit()
    printf "COUNT %d\n", calls
}
