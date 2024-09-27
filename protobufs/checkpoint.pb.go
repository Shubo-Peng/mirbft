// Code generated by protoc-gen-go. DO NOT EDIT.
// versions:
// 	protoc-gen-go v1.33.0-devel
// 	protoc        v3.12.4
// source: checkpoint.proto

package protobufs

import (
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	reflect "reflect"
	sync "sync"
)

const (
	// Verify that this generated code is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	// Verify that runtime/protoimpl is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

type CheckpointMsg struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	Sn        int32  `protobuf:"varint,1,opt,name=sn,proto3" json:"sn,omitempty"`
	Digest    []byte `protobuf:"bytes,2,opt,name=digest,proto3" json:"digest,omitempty"`
	Signature []byte `protobuf:"bytes,3,opt,name=signature,proto3" json:"signature,omitempty"`
}

func (x *CheckpointMsg) Reset() {
	*x = CheckpointMsg{}
	if protoimpl.UnsafeEnabled {
		mi := &file_checkpoint_proto_msgTypes[0]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *CheckpointMsg) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CheckpointMsg) ProtoMessage() {}

func (x *CheckpointMsg) ProtoReflect() protoreflect.Message {
	mi := &file_checkpoint_proto_msgTypes[0]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use CheckpointMsg.ProtoReflect.Descriptor instead.
func (*CheckpointMsg) Descriptor() ([]byte, []int) {
	return file_checkpoint_proto_rawDescGZIP(), []int{0}
}

func (x *CheckpointMsg) GetSn() int32 {
	if x != nil {
		return x.Sn
	}
	return 0
}

func (x *CheckpointMsg) GetDigest() []byte {
	if x != nil {
		return x.Digest
	}
	return nil
}

func (x *CheckpointMsg) GetSignature() []byte {
	if x != nil {
		return x.Signature
	}
	return nil
}

type StableCheckpoint struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	Sn    int32            `protobuf:"varint,1,opt,name=sn,proto3" json:"sn,omitempty"`
	Proof map[int32][]byte `protobuf:"bytes,2,rep,name=proof,proto3" json:"proof,omitempty" protobuf_key:"varint,1,opt,name=key,proto3" protobuf_val:"bytes,2,opt,name=value,proto3"`
}

func (x *StableCheckpoint) Reset() {
	*x = StableCheckpoint{}
	if protoimpl.UnsafeEnabled {
		mi := &file_checkpoint_proto_msgTypes[1]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *StableCheckpoint) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*StableCheckpoint) ProtoMessage() {}

func (x *StableCheckpoint) ProtoReflect() protoreflect.Message {
	mi := &file_checkpoint_proto_msgTypes[1]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use StableCheckpoint.ProtoReflect.Descriptor instead.
func (*StableCheckpoint) Descriptor() ([]byte, []int) {
	return file_checkpoint_proto_rawDescGZIP(), []int{1}
}

func (x *StableCheckpoint) GetSn() int32 {
	if x != nil {
		return x.Sn
	}
	return 0
}

func (x *StableCheckpoint) GetProof() map[int32][]byte {
	if x != nil {
		return x.Proof
	}
	return nil
}

var File_checkpoint_proto protoreflect.FileDescriptor

var file_checkpoint_proto_rawDesc = []byte{
	0x0a, 0x10, 0x63, 0x68, 0x65, 0x63, 0x6b, 0x70, 0x6f, 0x69, 0x6e, 0x74, 0x2e, 0x70, 0x72, 0x6f,
	0x74, 0x6f, 0x12, 0x09, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x62, 0x75, 0x66, 0x73, 0x22, 0x55, 0x0a,
	0x0d, 0x43, 0x68, 0x65, 0x63, 0x6b, 0x70, 0x6f, 0x69, 0x6e, 0x74, 0x4d, 0x73, 0x67, 0x12, 0x0e,
	0x0a, 0x02, 0x73, 0x6e, 0x18, 0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x02, 0x73, 0x6e, 0x12, 0x16,
	0x0a, 0x06, 0x64, 0x69, 0x67, 0x65, 0x73, 0x74, 0x18, 0x02, 0x20, 0x01, 0x28, 0x0c, 0x52, 0x06,
	0x64, 0x69, 0x67, 0x65, 0x73, 0x74, 0x12, 0x1c, 0x0a, 0x09, 0x73, 0x69, 0x67, 0x6e, 0x61, 0x74,
	0x75, 0x72, 0x65, 0x18, 0x03, 0x20, 0x01, 0x28, 0x0c, 0x52, 0x09, 0x73, 0x69, 0x67, 0x6e, 0x61,
	0x74, 0x75, 0x72, 0x65, 0x22, 0x9a, 0x01, 0x0a, 0x10, 0x53, 0x74, 0x61, 0x62, 0x6c, 0x65, 0x43,
	0x68, 0x65, 0x63, 0x6b, 0x70, 0x6f, 0x69, 0x6e, 0x74, 0x12, 0x0e, 0x0a, 0x02, 0x73, 0x6e, 0x18,
	0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x02, 0x73, 0x6e, 0x12, 0x3c, 0x0a, 0x05, 0x70, 0x72, 0x6f,
	0x6f, 0x66, 0x18, 0x02, 0x20, 0x03, 0x28, 0x0b, 0x32, 0x26, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f,
	0x62, 0x75, 0x66, 0x73, 0x2e, 0x53, 0x74, 0x61, 0x62, 0x6c, 0x65, 0x43, 0x68, 0x65, 0x63, 0x6b,
	0x70, 0x6f, 0x69, 0x6e, 0x74, 0x2e, 0x50, 0x72, 0x6f, 0x6f, 0x66, 0x45, 0x6e, 0x74, 0x72, 0x79,
	0x52, 0x05, 0x70, 0x72, 0x6f, 0x6f, 0x66, 0x1a, 0x38, 0x0a, 0x0a, 0x50, 0x72, 0x6f, 0x6f, 0x66,
	0x45, 0x6e, 0x74, 0x72, 0x79, 0x12, 0x10, 0x0a, 0x03, 0x6b, 0x65, 0x79, 0x18, 0x01, 0x20, 0x01,
	0x28, 0x05, 0x52, 0x03, 0x6b, 0x65, 0x79, 0x12, 0x14, 0x0a, 0x05, 0x76, 0x61, 0x6c, 0x75, 0x65,
	0x18, 0x02, 0x20, 0x01, 0x28, 0x0c, 0x52, 0x05, 0x76, 0x61, 0x6c, 0x75, 0x65, 0x3a, 0x02, 0x38,
	0x01, 0x42, 0x0e, 0x5a, 0x0c, 0x2e, 0x2f, 0x3b, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x62, 0x75, 0x66,
	0x73, 0x62, 0x06, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x33,
}

var (
	file_checkpoint_proto_rawDescOnce sync.Once
	file_checkpoint_proto_rawDescData = file_checkpoint_proto_rawDesc
)

func file_checkpoint_proto_rawDescGZIP() []byte {
	file_checkpoint_proto_rawDescOnce.Do(func() {
		file_checkpoint_proto_rawDescData = protoimpl.X.CompressGZIP(file_checkpoint_proto_rawDescData)
	})
	return file_checkpoint_proto_rawDescData
}

var file_checkpoint_proto_msgTypes = make([]protoimpl.MessageInfo, 3)
var file_checkpoint_proto_goTypes = []interface{}{
	(*CheckpointMsg)(nil),    // 0: protobufs.CheckpointMsg
	(*StableCheckpoint)(nil), // 1: protobufs.StableCheckpoint
	nil,                      // 2: protobufs.StableCheckpoint.ProofEntry
}
var file_checkpoint_proto_depIdxs = []int32{
	2, // 0: protobufs.StableCheckpoint.proof:type_name -> protobufs.StableCheckpoint.ProofEntry
	1, // [1:1] is the sub-list for method output_type
	1, // [1:1] is the sub-list for method input_type
	1, // [1:1] is the sub-list for extension type_name
	1, // [1:1] is the sub-list for extension extendee
	0, // [0:1] is the sub-list for field type_name
}

func init() { file_checkpoint_proto_init() }
func file_checkpoint_proto_init() {
	if File_checkpoint_proto != nil {
		return
	}
	if !protoimpl.UnsafeEnabled {
		file_checkpoint_proto_msgTypes[0].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*CheckpointMsg); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_checkpoint_proto_msgTypes[1].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*StableCheckpoint); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_checkpoint_proto_rawDesc,
			NumEnums:      0,
			NumMessages:   3,
			NumExtensions: 0,
			NumServices:   0,
		},
		GoTypes:           file_checkpoint_proto_goTypes,
		DependencyIndexes: file_checkpoint_proto_depIdxs,
		MessageInfos:      file_checkpoint_proto_msgTypes,
	}.Build()
	File_checkpoint_proto = out.File
	file_checkpoint_proto_rawDesc = nil
	file_checkpoint_proto_goTypes = nil
	file_checkpoint_proto_depIdxs = nil
}
