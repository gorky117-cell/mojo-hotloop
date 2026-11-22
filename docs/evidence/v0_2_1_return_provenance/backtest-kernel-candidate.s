
/tmp/hotloop-provenance/final-performance/candidate-1/fast.so:     file format elf64-x86-64


Disassembly of section .text:

0000000000001920 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])>:
    1920:	push   %rax
    1921:	mov    %rdi,%rax
    1924:	test   %rsi,%rsi
    1927:	jle    1a5b <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x13b>
    192d:	vmovsd 0xe6cb(%rip),%xmm3        # 10000 <_fini+0x6a0>
    1935:	vxorpd %xmm4,%xmm4,%xmm4
    1939:	vucomisd %xmm4,%xmm1
    193d:	jbe    1a6d <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x14d>
    1943:	vsubsd %xmm2,%xmm3,%xmm2
    1947:	vsubsd %xmm1,%xmm3,%xmm5
    194b:	mov    $0xfffffffffffffffe,%rdi
    1952:	mov    $0x1,%r8d
    1958:	mov    $0x1,%r9b
    195b:	mov    $0x2a,%ecx
    1960:	xor    %edx,%edx
    1962:	vmovsd 0xe69e(%rip),%xmm6        # 10008 <_fini+0x6a8>
    196a:	vmovsd 0xe69e(%rip),%xmm7        # 10010 <_fini+0x6b0>
    1972:	vmovsd 0xe69e(%rip),%xmm9        # 10018 <_fini+0x6b8>
    197a:	vmovapd %xmm3,%xmm10
    197e:	vxorpd %xmm1,%xmm1,%xmm1
    1982:	vmovapd %xmm0,%xmm8
    1986:	jmp    199d <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x7d>
    1988:	nopl   0x0(%rax,%rax,1)
    1990:	vmovapd %xmm8,%xmm0
    1994:	dec    %rsi
    1997:	je     1ac7 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1a7>
    199d:	imul   $0x19660d,%ecx,%ecx
    19a3:	add    $0x3c6ef35f,%ecx
    19a9:	vcvtsi2sd %rcx,%xmm15,%xmm11
    19ae:	vmulsd %xmm6,%xmm11,%xmm11
    19b2:	vaddsd %xmm7,%xmm11,%xmm11
    19b6:	vmulsd %xmm9,%xmm11,%xmm11
    19bb:	vaddsd %xmm3,%xmm11,%xmm11
    19bf:	vmulsd %xmm11,%xmm8,%xmm8
    19c4:	test   $0x1,%r9b
    19c8:	je     1a10 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0xf0>
    19ca:	mov    $0x1,%r9b
    19cd:	vucomisd %xmm0,%xmm8
    19d1:	ja     1990 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x70>
    19d3:	vmulsd %xmm0,%xmm5,%xmm11
    19d7:	vucomisd %xmm8,%xmm11
    19dc:	jb     1994 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    19de:	vmulsd %xmm8,%xmm10,%xmm1
    19e3:	vmulsd %xmm1,%xmm2,%xmm1
    19e7:	mov    $0x5,%edx
    19ec:	vxorpd %xmm10,%xmm10,%xmm10
    19f1:	mov    $0xffffffffffffffff,%rdi
    19f8:	xor    %r9d,%r9d
    19fb:	mov    $0xffffffffffffffff,%r8
    1a02:	jmp    1994 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    1a04:	data16 data16 cs nopw 0x0(%rax,%rax,1)
    1a10:	xor    %r9d,%r9d
    1a13:	test   %rdx,%rdx
    1a16:	setg   %r9b
    1a1a:	sub    %r9,%rdx
    1a1d:	je     1a27 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x107>
    1a1f:	xor    %r9d,%r9d
    1a22:	jmp    1994 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    1a27:	vucomisd %xmm4,%xmm8
    1a2b:	jne    1a33 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x113>
    1a2d:	jnp    1b0a <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1ea>
    1a33:	vmulsd %xmm1,%xmm2,%xmm0
    1a37:	vdivsd %xmm8,%xmm0,%xmm10
    1a3c:	mov    $0x1,%r9b
    1a3f:	vxorpd %xmm1,%xmm1,%xmm1
    1a43:	mov    $0x17,%r8d
    1a49:	mov    $0xfffffffffffffffe,%rdi
    1a50:	vmovapd %xmm8,%xmm0
    1a54:	xor    %edx,%edx
    1a56:	jmp    1994 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x74>
    1a5b:	mov    $0xffffffffffffffff,%r8
    1a62:	mov    $0x1,%edi
    1a67:	vmovapd %xmm0,%xmm1
    1a6b:	jmp    1adf <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1bf>
    1a6d:	mov    $0x2a,%ecx
    1a72:	vmovsd 0xe58e(%rip),%xmm1        # 10008 <_fini+0x6a8>
    1a7a:	vmovsd 0xe58e(%rip),%xmm2        # 10010 <_fini+0x6b0>
    1a82:	vmovsd 0xe58e(%rip),%xmm4        # 10018 <_fini+0x6b8>
    1a8a:	nopw   0x0(%rax,%rax,1)
    1a90:	imul   $0x19660d,%ecx,%ecx
    1a96:	add    $0x3c6ef35f,%ecx
    1a9c:	vcvtsi2sd %rcx,%xmm15,%xmm5
    1aa1:	vmulsd %xmm1,%xmm5,%xmm5
    1aa5:	vaddsd %xmm2,%xmm5,%xmm5
    1aa9:	vmulsd %xmm4,%xmm5,%xmm5
    1aad:	vaddsd %xmm3,%xmm5,%xmm5
    1ab1:	vmulsd %xmm5,%xmm0,%xmm0
    1ab5:	dec    %rsi
    1ab8:	jne    1a90 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x170>
    1aba:	mov    $0xffffffffffffffff,%rdi
    1ac1:	vmovapd %xmm0,%xmm1
    1ac5:	jmp    1ad8 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1b8>
    1ac7:	test   %r9b,%r9b
    1aca:	je     1adf <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1bf>
    1acc:	vmulsd %xmm10,%xmm8,%xmm1
    1ad1:	mov    $0xffffffffffffffff,%rdi
    1ad8:	mov    $0xffffffffffffffff,%r8
    1adf:	xor    %esi,%esi
    1ae1:	mov    %r11,0x20(%rax)
    1ae5:	mov    %r10,0x28(%rax)
    1ae9:	vmovsd %xmm1,0x8(%rax)
    1aee:	and    $0x1,%sil
    1af2:	mov    %sil,(%rax)
    1af5:	mov    %r9,0x30(%rax)
    1af9:	mov    %rdi,0x10(%rax)
    1afd:	mov    %rcx,0x38(%rax)
    1b01:	mov    %r8,0x18(%rax)
    1b05:	mov    %dl,0x40(%rax)
    1b08:	pop    %rcx
    1b09:	ret
    1b0a:	xor    %edi,%edi
    1b0c:	mov    %rax,(%rsp)
    1b10:	call   1b40 <std::builtin::error::StackTrace::collect_if_enabled(::SIMD[DType.int, 1])>
    1b15:	mov    %rax,%rcx
    1b18:	mov    (%rsp),%rax
    1b1c:	mov    $0x1,%sil
    1b1f:	movabs $0x2000000000000000,%r9
    1b29:	mov    $0x33,%r10d
    1b2f:	lea    0xe64a(%rip),%r11        # 10180 <static_string_3a20ef3aad3e5832>
    1b36:	jmp    1ae1 <fast::_native_return_origin_stateful_trailing_backtest(::SIMD[DType.int, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1],::SIMD[DType.float64, 1])+0x1c1>
