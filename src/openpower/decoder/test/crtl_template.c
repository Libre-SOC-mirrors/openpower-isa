#include <stdint.h>
#include "common.h"

state_t slots[%d];
uint64_t pending[%d];
uint64_t pending_count;

void add_pending(uint64_t index)
{
    pending[pending_count++] = index;
}

void clear_pending(void)
{
    pending_count = 0;
}

uint64_t capture(uint64_t index)
{
    if (slots[index].curr == slots[index].next)
        return 0;

    slots[index].curr = slots[index].next;
    return 1;
}

uint64_t get_curr(uint64_t index)
{
    return slots[index].curr;
}

uint64_t get_next(uint64_t index)
{
    return slots[index].next;
}

void set(uint64_t index, uint64_t value)
{
    slots[index].next = value;
    add_pending(index);
}
