
#ifndef _CLICK_SYNC_BARRIER_H
#define _CLICK_SYNC_BARRIER_H

#include "click_sync_types.h"

int wait_at_barrier(struct sync_data *data, struct sync_thread *thread);

#endif