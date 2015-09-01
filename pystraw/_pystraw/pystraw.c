
#include <stdint.h>
#include <xen/grant_table.h>
#include <xen/gntalloc.h>

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <assert.h>

#define NUM_STRAW_REFS    8
#define PAGE_SIZE         4096
#define STRAW_RING_SIZE		(NUM_STRAW_REFS/2*PAGE_SIZE -8)

typedef struct straw_ring_t straw_ring_t;
struct straw_ring_t {
	int32_t in_prod;
	int32_t in_cons;
	int32_t out_cons;
	int32_t out_prod;
	uint8_t input[STRAW_RING_SIZE];
	uint8_t output[STRAW_RING_SIZE];
};

void *pore_straw_open(domid_t domid, grant_ref_t refs[NUM_STRAW_REFS], uint32_t *evtchn)
{
    int fd = open("/dev/xen/gntalloc", O_RDWR);
    struct ioctl_gntalloc_alloc_gref op = {
        .domid = domid,
        .flags = GNTALLOC_FLAG_WRITABLE,
        .count = NUM_STRAW_REFS
    };

    int rs = ioctl(fd, IOCTL_GNTALLOC_ALLOC_GREF, &op);
    assert(rs == 0);

    void *ring = mmap(0, NUM_STRAW_REFS*PAGE_SIZE,
          PROT_READ | PROT_WRITE, MAP_SHARED, fd, op.index);
    assert(ring != MAP_FAILED);

    for (int i = 0; i < NUM_STRAW_REFS; i++)
        refs[i] = op.gref_ids[i];
    
    close(fd);

    //TODO split into two function
    //TODO we need to return both fd and event channel number

    //TODO allocate event channel
    *evtchn = 7;

    return ring;
}

