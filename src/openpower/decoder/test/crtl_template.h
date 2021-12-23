typedef struct state_t
{
    uint64_t curr;
    uint64_t next;
} state_t;

extern state_t slots[%d];
extern uint64_t pending[%d];
extern uint64_t pending_count;

void add_pending(uint64_t index);
void clear_pending(void);

uint64_t capture(uint64_t index);
uint64_t get_curr(uint64_t index);
uint64_t get_next(uint64_t index);
void set(uint64_t index, uint64_t value);
