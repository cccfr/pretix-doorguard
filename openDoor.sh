function open {
    gpio write 3 1
    sleep 3
    gpio write 3 0
}

open &
