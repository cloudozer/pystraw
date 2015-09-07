
#include <stdint.h>
#include <xen/grant_table.h>
#include <xen/gntalloc.h>
#include <xen/sys/gntalloc.h>
#include <xen/sys/evtchn.h>

#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <alloca.h>
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

void *pore_straw_ring_refs(domid_t domid, grant_ref_t refs[NUM_STRAW_REFS])
{
    int fd = open("/dev/xen/gntalloc", O_RDWR);

    struct ioctl_gntalloc_alloc_gref *op;
    int size = sizeof(*op) + sizeof(grant_ref_t) *NUM_STRAW_REFS;
    op = (struct ioctl_gntalloc_alloc_gref *)alloca(size);
    op->domid = domid;
    op->flags = GNTALLOC_FLAG_WRITABLE;
    op->count = NUM_STRAW_REFS;

    int rs = ioctl(fd, IOCTL_GNTALLOC_ALLOC_GREF, op);
    assert(rs == 0);

    void *ring = mmap(0, NUM_STRAW_REFS *PAGE_SIZE,
                        PROT_READ | PROT_WRITE, MAP_SHARED, fd, op->index);
    assert(ring != MAP_FAILED);

    for (int i = 0; i < NUM_STRAW_REFS; i++)
        refs[i] = op->gref_ids[i];
    
    close(fd);

    return ring;
}

int pore_straw_alloc_unbound(domid_t domid, int fd)
{
    struct ioctl_evtchn_bind_unbound_port bind = {
        .remote_domain = domid,
    };

    return ioctl(fd, IOCTL_EVTCHN_BIND_UNBOUND_PORT, &bind);
}

int pore_straw_poke(uint32_t port, int fd)
{
    struct ioctl_evtchn_notify notify = {
        .port = port,
    };

    return ioctl(fd, IOCTL_EVTCHN_NOTIFY, &notify);
}

int pore_straw_unbind_port(uint32_t port, int fd)
{
    struct ioctl_evtchn_unbind unbind = {
        .port = port,
    };

    return ioctl(fd, IOCTL_EVTCHN_UNBIND, &unbind); 
}

void pore_straw_avail(straw_ring_t *ring, int *ia, int *oa)
{
    //TODO: this works for active mode only
    int avail1 = ring->in_prod - ring->in_cons;
    while (avail1 < 0)
        avail1 += STRAW_RING_SIZE;
    int avail2 = ring->out_cons - ring->out_prod;
    while (avail2 <= 0)
        avail2 += STRAW_RING_SIZE;
    avail2--; // unused byte

    *ia = avail1;
    *oa = avail2;
}

int pore_straw_read(straw_ring_t *ring, uint8_t *data, int len)
{
    assert(len >= STRAW_RING_SIZE);
    int prod = ring->in_prod;
    int cons = ring->in_cons;
    int avail = prod - cons;
    while (avail < 0)
        avail += STRAW_RING_SIZE;
    //rmb();
    uint8_t *buffer = ring->input;
    int read = 0;
    while (avail-- > 0)
    {
        *data++ = buffer[cons++];
        read++;
        if (cons >= STRAW_RING_SIZE)
            cons = 0;
    }
    //mb();
    ring->in_cons = cons;
    return read;
}

void pore_straw_write(straw_ring_t *ring, uint8_t *data, int len)
{
    int prod = ring->out_prod;
    int cons = ring->out_cons;
    //mb();
    uint8_t *buffer = ring->output;
    while (len-- > 0)
    {
        buffer[prod++] = *data++;
        if (prod == STRAW_RING_SIZE)
            prod = 0;
    }
    //wmb();
    ring->out_prod = prod;
}

