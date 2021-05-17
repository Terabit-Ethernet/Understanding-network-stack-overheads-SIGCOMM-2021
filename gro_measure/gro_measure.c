#include <linux/netfilter.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/netfilter_ipv4.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <linux/tcp.h>
#include <linux/inet.h>

static int gro_gen __read_mostly = 0;
module_param(gro_gen, int, 0644);
MODULE_PARM_DESC(gro_gen, "count gro distribution skb");

long sysctl_tcp_histo[13] __read_mostly;

unsigned int my_hookfn(void *priv, struct sk_buff *skb, const struct nf_hook_state *state)
{
	struct iphdr *iph = ip_hdr(skb);  
	static long total = 0;
	if (gro_gen > 0) {
		if(iph->saddr == in_aton("192.168.10.114") &&
				iph->daddr == in_aton("192.168.10.115")) {
			unsigned int size = 0;
			if (!sysctl_tcp_histo[0])
				sysctl_tcp_histo[0] = 1;
			if(total == 2000000) {
				int i;
				printk("%ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld %ld\n",
		                                sysctl_tcp_histo[0],
		                                sysctl_tcp_histo[1],
		                                sysctl_tcp_histo[2],
		                                sysctl_tcp_histo[3],
		                                sysctl_tcp_histo[4],
		                                sysctl_tcp_histo[5],
		                                sysctl_tcp_histo[6],
		                                sysctl_tcp_histo[7],
		                                sysctl_tcp_histo[8],
		                                sysctl_tcp_histo[9],
		                                sysctl_tcp_histo[10],
		                                sysctl_tcp_histo[11],
		                                sysctl_tcp_histo[12]);
				for (i=0; i<13; i++)
					sysctl_tcp_histo[i] = 0;
				total = 0;
			}
			// printk("total:%ld\n", total);
			if (skb->len > 300) {
				if (skb->data_len)
					size = skb->data_len;
				else
					size = skb->len;
			}
			if (size >= 60000)
                    sysctl_tcp_histo[12]++;
            else if (size >= 55000)
                    sysctl_tcp_histo[11]++;
            else if (size >= 50000)
                    sysctl_tcp_histo[10]++;
            else if (size >= 45000)
                    sysctl_tcp_histo[9]++;
            else if (size >= 40000)
                    sysctl_tcp_histo[8]++;
            else if (size >= 35000)
                    sysctl_tcp_histo[7]++;
            else if (size >= 30000)
                    sysctl_tcp_histo[6]++;
            else if (size >= 25000)
                    sysctl_tcp_histo[5]++;
            else if (size >= 20000)
                    sysctl_tcp_histo[4]++;
            else if (size >= 15000)
                    sysctl_tcp_histo[3]++;
            else if (size >= 10000)
                    sysctl_tcp_histo[2]++;
            else if (size >= 5000)
                    sysctl_tcp_histo[1]++;
            else if (size >= 500)
                    sysctl_tcp_histo[0]++;
            total += 1;
    	}
	} 
	return NF_ACCEPT;
}

/* A netfilter instance to use */
static struct nf_hook_ops nfho = {
    .hook = my_hookfn,
    .pf = PF_INET,
    .hooknum = NF_INET_PRE_ROUTING,
    .priority = NF_IP_PRI_FIRST,
};

static int __init sknf_init(void)
{
    if (nf_register_net_hook(&init_net, &nfho)) {
        printk(KERN_ERR"nf_register_hook() failed\n");
        return -1;
    }else{
        printk(KERN_INFO "Loading filter module\n");
    }

    return 0;
}

static void __exit sknf_exit(void)
{
	nf_unregister_net_hook(&init_net, &nfho);
}

module_init(sknf_init);
module_exit(sknf_exit);
MODULE_AUTHOR("Qizhe Cai");
MODULE_LICENSE("GPL");
